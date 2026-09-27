"""Deterministic summary engine for file and folder entities.

Every claim is derived from AST facts already computed at import time
(syntax.json) or from the inventory (line counts, languages).  No model
inference is needed for the core summary; citations are therefore true by
construction.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel

from app.services.inventory_service import entity_id
from app.services.snapshot_service import (
    get_file_record,
    get_inventory,
    get_syntax_records,
    read_source_lines,
)
from app.services.v1_errors import WorkspaceError


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class SourceRange(BaseModel):
    line_start: int
    line_end: int


class EvidenceItem(BaseModel):
    id: str
    snapshot_id: str
    file_id: str
    path: str
    range: SourceRange
    content_sha256: str
    basis: str  # 'observed' | 'resolved' | 'inferred'


class SummaryPayload(BaseModel):
    schema_version: str = '1.1'
    snapshot_id: str
    entity_id: str
    text: str
    evidence: list[EvidenceItem]
    limitations: list[str]


# ---------------------------------------------------------------------------
# Internal claim builder
# ---------------------------------------------------------------------------

def _make_evidence(snapshot_id: str, file_id: str, path: str,
                   line_start: int, line_end: int, content_sha256: str,
                   basis: str = 'observed') -> EvidenceItem:
    return EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snapshot_id,
        file_id=file_id,
        path=path,
        range=SourceRange(line_start=line_start, line_end=line_end),
        content_sha256=content_sha256,
        basis=basis,
    )


def _extract_docstring_lines(content: str) -> tuple[int, int] | None:
    """Return (line_start, line_end) of the module-level docstring, 1-based.

    Only looks at the first non-empty, non-comment lines.  Returns None if
    no docstring is found in the first 80 lines.
    """
    lines = content.splitlines()
    in_triple = False
    start: int | None = None
    quote_char: str | None = None

    for i, raw in enumerate(lines[:80], start=1):
        stripped = raw.strip()
        if not in_triple:
            if not stripped or stripped.startswith('#'):
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote_char = stripped[:3]
                # same-line close?
                rest = stripped[3:]
                if rest.endswith(quote_char) and len(rest) >= 0:
                    # single-line triple-quoted string
                    return (i, i)
                in_triple = True
                start = i
            else:
                # first statement is not a docstring
                return None
        else:
            if quote_char and quote_char in raw:
                return (start, i)  # type: ignore[return-value]
    return None


def _summarise_file(snapshot_id: str, path: str) -> SummaryPayload:
    """Build a deterministic summary for a single file."""
    rec = None
    for r in get_inventory(snapshot_id, limit=10000).files:
        if r.path == path:
            rec = r
            break
    if rec is None:
        raise WorkspaceError('NOT_FOUND', f"Path '{path}' not found in snapshot.", 404)
    if rec.excluded:
        raise WorkspaceError('NOT_FOUND', f"Path '{path}' is excluded from this snapshot.", 404)

    eid = entity_id(snapshot_id, path, 'file')
    evidence: list[EvidenceItem] = []
    claims: list[str] = []
    limitations: list[str] = []

    total_lines = 0
    # Read source to get total line count and docstring
    if rec.is_text:
        try:
            src_slice = read_source_lines(snapshot_id, rec.id, 1, None, max_lines=2000)
            total_lines = src_slice.total_lines
            content = src_slice.content
            # Module docstring
            doc_range = _extract_docstring_lines(content)
            if doc_range is not None:
                ds_start, ds_end = doc_range
                ev = _make_evidence(snapshot_id, rec.id, path, ds_start, ds_end, rec.content_hash)
                evidence.append(ev)
                claims.append(
                    f'Module docstring found at lines {ds_start}–{ds_end} [{ev.id}].'
                )
        except WorkspaceError as err:
            limitations.append(f'Source read failed: {err.message}')

    claims.insert(0, f'{path} is a {rec.language} file with {total_lines} lines.')

    # Functions and classes from syntax records
    syntax = get_syntax_records(snapshot_id)
    if rec.id in syntax:
        file_obj = syntax[rec.id]
        for fn in file_obj.functions:
            ev = _make_evidence(snapshot_id, rec.id, path, fn.line_start, fn.line_end, rec.content_hash)
            evidence.append(ev)
            calls_text = ''
            if fn.calls:
                calls_text = f' Calls: {", ".join(fn.calls[:10])}.'
                if len(fn.calls) > 10:
                    calls_text += f' (and {len(fn.calls) - 10} more)'
            claims.append(
                f'Function `{fn.name}` defined at lines {fn.line_start}–{fn.line_end} [{ev.id}].{calls_text}'
            )
        for cls in file_obj.classes:
            ev = _make_evidence(snapshot_id, rec.id, path, cls.line_start, cls.line_end, rec.content_hash)
            evidence.append(ev)
            claims.append(
                f'Class `{cls.name}` defined at lines {cls.line_start}–{cls.line_end} [{ev.id}].'
            )
        if file_obj.imports:
            # Imports are stored as module names, not line numbers — emit as inferred
            import_list = ', '.join(f'`{imp}`' for imp in file_obj.imports[:20])
            claims.append(f'Imports: {import_list}.')
            if len(file_obj.imports) > 20:
                claims.append(f'({len(file_obj.imports) - 20} additional imports omitted.)')
    else:
        if rec.is_text:
            limitations.append('Syntax extraction is not available for this file; function and class details omitted.')

    text = '\n'.join(claims)
    return SummaryPayload(
        snapshot_id=snapshot_id,
        entity_id=eid,
        text=text,
        evidence=evidence,
        limitations=limitations,
    )


def _summarise_folder(snapshot_id: str, path: str) -> SummaryPayload:
    """Build a deterministic summary for a folder (or repository root '.')."""
    all_records = get_inventory(snapshot_id, limit=10000).files
    # Filter files under this folder
    if path == '.':
        children = all_records
    else:
        prefix = path.rstrip('/') + '/'
        children = [r for r in all_records if r.path.startswith(prefix)]

    if not children and path != '.':
        raise WorkspaceError('NOT_FOUND', f"Folder '{path}' not found in snapshot.", 404)

    eid = entity_id(snapshot_id, path, 'repository' if path == '.' else 'folder')
    evidence: list[EvidenceItem] = []
    claims: list[str] = []
    limitations: list[str] = []

    non_excluded = [r for r in children if not r.excluded]
    total_lines = 0
    languages: dict[str, int] = {}
    symbol_names: list[str] = []

    syntax = get_syntax_records(snapshot_id)
    for rec in non_excluded:
        # Count lines
        if rec.is_text:
            try:
                sl = read_source_lines(snapshot_id, rec.id, 1, 1, max_lines=1)
                total_lines += sl.total_lines
                ev = _make_evidence(snapshot_id, rec.id, rec.path, 1, sl.total_lines, rec.content_hash)
                evidence.append(ev)
            except WorkspaceError:
                pass
        languages[rec.language] = languages.get(rec.language, 0) + 1
        # Collect top-level symbols
        if rec.id in syntax:
            file_obj = syntax[rec.id]
            for fn in file_obj.functions:
                symbol_names.append(fn.name)
            for cls in file_obj.classes:
                symbol_names.append(cls.name)

    folder_label = 'repository root' if path == '.' else f'folder `{path}`'
    lang_summary = ', '.join(f'{lang} ({count})' for lang, count in sorted(languages.items(), key=lambda x: -x[1]))
    claims.append(
        f'The {folder_label} contains {len(non_excluded)} files with {total_lines} total lines.'
    )
    if lang_summary:
        claims.append(f'Languages present: {lang_summary}.')
    distinct_symbols = sorted(set(symbol_names))
    if distinct_symbols:
        sample = distinct_symbols[:30]
        claims.append(f'Top-level symbols ({len(distinct_symbols)} total): {", ".join(f"`{s}`" for s in sample)}.')
        if len(distinct_symbols) > 30:
            claims.append(f'({len(distinct_symbols) - 30} additional symbols not listed.)')
    if [r for r in children if r.excluded]:
        excluded_count = len([r for r in children if r.excluded])
        limitations.append(f'{excluded_count} file(s) excluded by source policy and not included in this summary.')

    text = '\n'.join(claims)
    return SummaryPayload(
        snapshot_id=snapshot_id,
        entity_id=eid,
        text=text,
        evidence=evidence,
        limitations=limitations,
    )


async def enrich(claims: str) -> str | None:
    """Optional AI enrichment hook. Returns None when not configured."""
    return None


async def build_summary(snapshot_id: str, path: str | None) -> SummaryPayload:
    """Entry point: build a deterministic summary and optionally enrich it."""
    resolved_path = path or '.'

    # Determine whether this is a file or folder by checking the inventory
    inventory = get_inventory(snapshot_id, limit=10000)
    file_paths = {r.path for r in inventory.files}
    folder_paths: set[str] = {'.'}
    for p in file_paths:
        parts = p.split('/')
        for depth in range(1, len(parts)):
            folder_paths.add('/'.join(parts[:depth]))

    if resolved_path in file_paths:
        payload = _summarise_file(snapshot_id, resolved_path)
    elif resolved_path in folder_paths:
        payload = _summarise_folder(snapshot_id, resolved_path)
    else:
        raise WorkspaceError('NOT_FOUND', f"Path '{resolved_path}' is not in this snapshot.", 404)

    enriched = await enrich(payload.text)
    if enriched is not None:
        payload = payload.model_copy(update={'text': enriched})

    return payload
