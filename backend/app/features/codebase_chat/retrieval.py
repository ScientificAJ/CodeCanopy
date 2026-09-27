"""Question-focused evidence retrieval across complete, verified source files.

The prompt is bounded; the search is not restricted to file prefixes. No source
is executed, and excluded files never reach either search or a model provider.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import heapq
import math
import re
import time

from pydantic import BaseModel
from app.services.snapshot_service import get_inventory, read_source_text
from app.services.v1_errors import WorkspaceError

MAX_CONTEXT_CHARS = 18_000
MAX_CHUNK_CHARS = 3_000
MAX_CHUNKS = 10
MAX_SEARCH_SECONDS = 25
STOP = set('the is are was a an of in to for and or not it this that what why how where which with by be do does can has have i my me its at on from file folder show tell give explain about here there used use code repository please function'.split())
OVERVIEW = {'overview', 'purpose', 'architecture', 'stack', 'packages', 'project', 'repository', 'does', 'explain'}


class SourceCitation(BaseModel):
    id: str
    file_id: str
    path: str
    line_start: int
    line_end: int


@dataclass
class Retrieval:
    context: str
    sources: list[SourceCitation]
    hint: str
    limitations: list[str]


def tokens(text):
    expanded = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    return set(re.findall(r'[a-zA-Z][a-zA-Z0-9_]{1,}', text.lower()) + re.findall(r'[a-zA-Z][a-zA-Z0-9]{1,}', expanded.replace('_', ' ').lower()))


def windows(lines):
    """Overlapping complete-line windows, including code deep inside long files."""
    start = 0
    while start < len(lines):
        end, size = start, 0
        while end < len(lines) and end - start < 70:
            cost = len(lines[end]) + len(str(end + 1)) + 3
            if size + cost > MAX_CHUNK_CHARS:
                break
            size += cost
            end += 1
        if end == start:
            # A minified/generated line cannot fit a source excerpt; never
            # disguise a partial line as a complete cited statement.
            start += 1
            continue
        yield start, end, '\n'.join(f'{i+1}: {lines[i]}' for i in range(start, end))
        if end == len(lines):
            break
        start = max(start + 1, end - 12)


def retrieve(snapshot_id, question, scope='repository', file_id=None, folder_path=None, history_question=''):
    records = get_inventory(snapshot_id, limit=None).files
    if scope == 'file':
        if not file_id:
            raise WorkspaceError('INVALID_SCOPE', 'Select a file before asking a file-scoped question.', 422)
        records = [r for r in records if r.id == file_id]
        if not records:
            raise WorkspaceError('NOT_FOUND', 'Selected file is not in this snapshot.', 404)
    elif scope == 'folder':
        if not folder_path or folder_path in ('.', '/'):
            raise WorkspaceError('INVALID_SCOPE', 'Select a folder before asking a folder-scoped question.', 422)
        prefix = folder_path.rstrip('/') + '/'
        records = [r for r in records if r.path.startswith(prefix)]
        if not records:
            raise WorkspaceError('NOT_FOUND', 'Selected folder is not in this snapshot.', 404)
    eligible = [r for r in records if r.is_text and not r.excluded]
    query = tokens(question) - STOP
    # Pronoun-style follow-ups retain the topic without reusing old source evidence.
    if len(query) < 3:
        query |= tokens(history_question) - STOP
    if tokens(question) & {'entry', 'entrypoint'}:
        query |= {'main', 'bin', 'scripts', 'exports'}
    query = set(sorted(query, key=lambda t: (-len(t), t))[:32])
    overview = bool(tokens(question) & OVERVIEW)
    scope_depth = folder_path.rstrip('/').count('/') + 1 if scope == 'folder' else 0
    # Inspect top-level documentation first so a bounded search still covers the
    # project's own introduction before nested package docs and generated files.
    if overview:
        eligible.sort(key=lambda r: (r.path.count('/') - scope_depth, r.name.lower() not in {'readme.md', 'readme.rst', 'package.json', 'pyproject.toml'}, r.path))
    heap = []
    serial = 0
    scanned = 0
    unavailable = 0
    long_lines = 0
    deadline = time.monotonic() + MAX_SEARCH_SECONDS
    for rec in eligible:
        if time.monotonic() > deadline:
            break
        try:
            _, text = read_source_text(snapshot_id, rec.id)
        except WorkspaceError:
            unavailable += 1
            continue
        lines = text.splitlines()
        scanned += 1
        long_lines += sum(len(line) + len(str(i+1)) + 3 > MAX_CHUNK_CHARS for i, line in enumerate(lines))
        path_hits = len(query & tokens(rec.path))
        is_manifest = rec.name.lower() in {'readme.md', 'readme.rst', 'package.json', 'pyproject.toml', 'cargo.toml', 'go.mod', 'requirements.txt'}
        for start, end, excerpt in windows(lines):
            counts = Counter(re.findall(r'[a-zA-Z][a-zA-Z0-9_]{1,}', excerpt.lower()))
            matches = query & tokens(excerpt)
            score = sum(4 + math.log1p(min(counts.get(term, 1), 5)) for term in matches) + path_hits * 2
            if start == 0:
                score += 1
                if overview and is_manifest:
                    depth = max(0, rec.path.count('/') - scope_depth)
                    score += (180 if rec.name.lower() in {'readme.md', 'readme.rst'} else 100) / (1 + depth * 3)
            # Keep representative sections for general file explanations, too.
            if scope == 'file' and not matches:
                score += 1 / (1 + abs(start - len(lines) / 2))
            serial += 1
            item = (score, -serial, rec.id, rec.path, start + 1, end, excerpt)
            if len(heap) < 160:
                heapq.heappush(heap, item)
            elif item[:2] > heap[0][:2]:
                heapq.heapreplace(heap, item)
    chosen = []
    file_counts = Counter()
    size = 0
    for _, _, fid, path, start, end, excerpt in sorted(heap, reverse=True):
        if file_counts[fid] >= (MAX_CHUNKS if scope == 'file' else 3):
            continue
        if any(old.file_id == fid and max(start, old.line_start) <= min(end, old.line_end) for old, _ in chosen):
            continue
        citation = SourceCitation(id=f'S{len(chosen)+1}', file_id=fid, path=path, line_start=start, line_end=end)
        block = f'[{citation.id}] {path} lines {start}-{end}\n{excerpt}'
        if size + len(block) > MAX_CONTEXT_CHARS:
            continue
        chosen.append((citation, block)); size += len(block); file_counts[fid] += 1
        if len(chosen) >= MAX_CHUNKS:
            break
    limitations = []
    if scanned + unavailable < len(eligible):
        limitations.append(f'Search time budget reached after {scanned} of {len(eligible)} eligible files; coverage is partial.')
    if unavailable:
        limitations.append(f'{unavailable} file(s) could not pass source availability/integrity checks.')
    if long_lines:
        limitations.append(f'{long_lines} oversized source line(s) were omitted from excerpts; use the source viewer to inspect them.')
    if not chosen:
        limitations.append('No readable source evidence is available within this scope.')
    hint = f'Searched {scanned} of {len(eligible)} eligible files; selected {len(chosen)} source passages from {len(file_counts)} files.'
    return Retrieval('\n\n'.join(block for _, block in chosen), [c for c, _ in chosen], hint, limitations)
