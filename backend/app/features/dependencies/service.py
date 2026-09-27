"""Dependency graph builder for a snapshot.

Builds import-level edges from the pre-computed syntax records.
Never re-parses source — all structural data comes from syntax.json.

Import line numbers are recovered by scanning source lines for the
specifier string, since the ``imports`` field in the syntax record
stores module-name strings only (no line metadata).

The 'never fabricate a target' rule is enforced throughout: if a
specifier does not resolve to a real FileRecord in this snapshot the
edge is unresolved and the reason is recorded.
"""
from __future__ import annotations

import asyncio
import posixpath
import re
import uuid

from pydantic import BaseModel

from app.services.inventory_service import entity_id
from app.services.snapshot_service import (
    get_inventory,
    get_syntax_records,
    read_source_lines,
)
from app.services.v1_errors import WorkspaceError

# Recognised source suffixes tried when resolving a relative import
_SUFFIXES = [
    '', '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
]
# Index variants tried for each candidate path (bare dir + /index.*)
_INDEX_NAMES = [
    'index.py', 'index.js', 'index.ts', 'index.tsx', 'index.jsx',
]

IMPACT_WALK_CAP = 500


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
    basis: str  # always 'resolved' for import edges


class EdgeEndpoint(BaseModel):
    entity_id: str
    path: str
    file_id: str | None = None  # None for external/unresolved


class DependencyEdge(BaseModel):
    id: str
    source: EdgeEndpoint
    target: EdgeEndpoint
    kind: str  # 'imports' | 'calls'
    evidence_id: str | None = None


class UnresolvedRef(BaseModel):
    source_path: str
    specifier: str
    reason: str  # 'bare_package' | 'not_found'


class DependencyGraph(BaseModel):
    edges: list[DependencyEdge]
    unresolved: list[UnresolvedRef]
    evidence: list[EvidenceItem]


class DependencyOverlay(BaseModel):
    schema_version: str = '1.1'
    snapshot_id: str
    graph: DependencyGraph
    impact_subject_ids: list[str]
    limitations: list[str]


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve_python_specifier(
    specifier: str,
    importing_path: str,
    path_set: set[str],
) -> str | None:
    """Resolve a Python import specifier against the snapshot path set.

    Python relative specifiers start with dots: '.' means current package,
    '..' means parent, etc.  Absolute specifiers are treated as dotted
    module paths and tried against the path set.
    """
    if not specifier.startswith('.'):
        # absolute: convert dotted name to path
        as_path = specifier.replace('.', '/')
        for suffix in _SUFFIXES:
            candidate = as_path + suffix
            if candidate in path_set:
                return candidate
        for index_name in _INDEX_NAMES:
            candidate = as_path + '/' + index_name
            if candidate in path_set:
                return candidate
        return None

    # relative: count leading dots
    dot_count = len(specifier) - len(specifier.lstrip('.'))
    rest = specifier[dot_count:].replace('.', '/')
    # start from importing file's directory
    importing_dir = posixpath.dirname(importing_path)
    # go up (dot_count - 1) levels  (one dot = same package, two dots = parent)
    base = importing_dir
    for _ in range(dot_count - 1):
        base = posixpath.dirname(base)

    candidate_base = posixpath.join(base, rest).lstrip('/') if rest else base
    for suffix in _SUFFIXES:
        candidate = (candidate_base + suffix).lstrip('/')
        if candidate in path_set:
            return candidate
    for index_name in _INDEX_NAMES:
        candidate = (candidate_base + '/' + index_name).lstrip('/')
        if candidate in path_set:
            return candidate
    return None


def _resolve_js_specifier(
    specifier: str,
    importing_path: str,
    path_set: set[str],
) -> str | None:
    """Resolve a JS/TS import specifier."""
    if not specifier.startswith('.'):
        return None  # bare package — caller records as bare_package

    importing_dir = posixpath.dirname(importing_path)
    raw = posixpath.normpath(posixpath.join(importing_dir, specifier)).replace('\\', '/')
    for suffix in _SUFFIXES:
        candidate = (raw + suffix).lstrip('/')
        if candidate in path_set:
            return candidate
    for index_name in _INDEX_NAMES:
        candidate = (raw + '/' + index_name).lstrip('/')
        if candidate in path_set:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Import-line finder
# ---------------------------------------------------------------------------

def _find_import_line(
    snapshot_id: str,
    file_id: str,
    specifier: str,
    language: str,
) -> int | None:
    """Scan source lines for the line number of an import statement.

    Returns 1-based line number, or None if the source is unavailable or
    the specifier is not found.
    """
    try:
        sl = read_source_lines(snapshot_id, file_id, 1, None, max_lines=2000)
    except WorkspaceError:
        return None

    lines = sl.content.splitlines()
    escaped = re.escape(specifier)
    if language in ('javascript', 'typescript'):
        pattern = re.compile(r'\b(?:import|require)\b.*' + escaped)
    else:
        # Python
        pattern = re.compile(r'^\s*(?:from|import)\s+' + escaped + r'(?:\s|$|,|\()')

    for i, line in enumerate(lines, start=1):
        if pattern.search(line):
            return i
    # Fallback: specifier appears anywhere in an import/from statement
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if (stripped.startswith('import ') or stripped.startswith('from ')) and specifier in line:
            return i
    return None


# ---------------------------------------------------------------------------
# Graph builder (returns graph + metadata maps for the verifier)
# ---------------------------------------------------------------------------

def _build_graph_raw(
    snapshot_id: str,
) -> tuple[DependencyGraph, dict[str, str], dict[str, str]]:
    """Build the full import-edge dependency graph.

    Returns:
        (graph, edge_specifier_map, file_language_map)
        edge_specifier_map: edge_id → original specifier string
        file_language_map:  file_id → language
    """
    inventory = get_inventory(snapshot_id, limit=None)
    all_records = inventory.files
    path_set = {r.path for r in all_records if not r.excluded}
    record_by_path = {r.path: r for r in all_records if not r.excluded}

    syntax = get_syntax_records(snapshot_id)

    edges: list[DependencyEdge] = []
    unresolved: list[UnresolvedRef] = []
    evidence_list: list[EvidenceItem] = []
    edge_specifier_map: dict[str, str] = {}
    file_language_map: dict[str, str] = {r.id: r.language for r in all_records}

    for rec in all_records:
        if rec.excluded or rec.id not in syntax:
            continue
        file_obj = syntax[rec.id]
        if not file_obj.imports:
            continue

        language = rec.language
        for specifier in file_obj.imports:
            # Attempt resolution
            if language == 'python':
                if specifier.startswith('.'):
                    resolved_path = _resolve_python_specifier(specifier, rec.path, path_set)
                    if resolved_path is None:
                        unresolved.append(UnresolvedRef(
                            source_path=rec.path,
                            specifier=specifier,
                            reason='not_found',
                        ))
                        continue
                else:
                    resolved_path = _resolve_python_specifier(specifier, rec.path, path_set)
                    if resolved_path is None:
                        unresolved.append(UnresolvedRef(
                            source_path=rec.path,
                            specifier=specifier,
                            reason='bare_package',
                        ))
                        continue
            elif language in ('javascript', 'typescript'):
                if not specifier.startswith('.'):
                    unresolved.append(UnresolvedRef(
                        source_path=rec.path,
                        specifier=specifier,
                        reason='bare_package',
                    ))
                    continue
                resolved_path = _resolve_js_specifier(specifier, rec.path, path_set)
                if resolved_path is None:
                    unresolved.append(UnresolvedRef(
                        source_path=rec.path,
                        specifier=specifier,
                        reason='not_found',
                    ))
                    continue
            else:
                unresolved.append(UnresolvedRef(
                    source_path=rec.path,
                    specifier=specifier,
                    reason='not_found',
                ))
                continue

            target_rec = record_by_path.get(resolved_path)
            if target_rec is None:
                unresolved.append(UnresolvedRef(
                    source_path=rec.path,
                    specifier=specifier,
                    reason='not_found',
                ))
                continue

            # Find the import line in source
            line_no = _find_import_line(snapshot_id, rec.id, specifier, language)
            if line_no is None:
                unresolved.append(UnresolvedRef(
                    source_path=rec.path,
                    specifier=specifier,
                    reason='not_found',
                ))
                continue

            ev = EvidenceItem(
                id=uuid.uuid4().hex,
                snapshot_id=snapshot_id,
                file_id=rec.id,
                path=rec.path,
                range=SourceRange(line_start=line_no, line_end=line_no),
                content_sha256=rec.content_hash,
                basis='resolved',
            )
            evidence_list.append(ev)

            source_eid = entity_id(snapshot_id, rec.path, 'file')
            target_eid = entity_id(snapshot_id, target_rec.path, 'file')
            edge_id = uuid.uuid4().hex

            edges.append(DependencyEdge(
                id=edge_id,
                source=EdgeEndpoint(entity_id=source_eid, path=rec.path, file_id=rec.id),
                target=EdgeEndpoint(entity_id=target_eid, path=target_rec.path, file_id=target_rec.id),
                kind='imports',
                evidence_id=ev.id,
            ))
            edge_specifier_map[edge_id] = specifier

    graph = DependencyGraph(edges=edges, unresolved=unresolved, evidence=evidence_list)
    return graph, edge_specifier_map, file_language_map


# ---------------------------------------------------------------------------
# Change impact
# ---------------------------------------------------------------------------

def compute_impact(
    snapshot_id: str,
    graph: DependencyGraph,
    subject_path: str,
) -> tuple[list[str], bool]:
    """Return (affected_entity_ids, truncated).

    Walks import edges in reverse: finds all files that transitively
    import the subject.  Returns entity_ids.  Capped at IMPACT_WALK_CAP.
    """
    inventory = get_inventory(snapshot_id, limit=None)
    all_records = inventory.files
    path_to_eid = {r.path: entity_id(snapshot_id, r.path, 'file') for r in all_records}

    path_set = {r.path for r in all_records}
    if subject_path in path_set:
        subject_paths = {subject_path}
    else:
        prefix = subject_path.rstrip('/') + '/'
        subject_paths = {p for p in path_set if p == subject_path or p.startswith(prefix)}

    # Build reverse adjacency: target_path → set of source_paths
    reverse: dict[str, set[str]] = {}
    for edge in graph.edges:
        reverse.setdefault(edge.target.path, set()).add(edge.source.path)

    # BFS
    visited: set[str] = set()
    queue = list(subject_paths)
    truncated = False

    while queue and len(visited) < IMPACT_WALK_CAP:
        current = queue.pop(0)
        importers = reverse.get(current, set())
        for imp in importers:
            if imp not in visited and imp not in subject_paths:
                visited.add(imp)
                queue.append(imp)

    if queue:
        truncated = True

    affected_ids = [path_to_eid[p] for p in visited if p in path_to_eid]
    return affected_ids, truncated


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _build_dependencies(
    snapshot_id: str,
    path: str | None,
    depth: int | None,
) -> DependencyOverlay:
    """Build the dependency overlay for the given snapshot and optional subject."""
    from app.features.dependencies.verifier import verify_dependency_edges

    # Validate path if given
    if path is not None:
        inventory = get_inventory(snapshot_id, limit=None)
        all_paths = {r.path for r in inventory.files}
        folder_paths: set[str] = {'.'}
        for p in all_paths:
            parts = p.split('/')
            for d in range(1, len(parts)):
                folder_paths.add('/'.join(parts[:d]))
        if path not in all_paths and path not in folder_paths:
            raise WorkspaceError('NOT_FOUND', f"Path '{path}' is not in this snapshot.", 404)

    raw_graph, edge_specifier_map, file_language_map = _build_graph_raw(snapshot_id)

    # Verify edges — unverified ones are removed
    verified_graph, report = verify_dependency_edges(
        snapshot_id,
        raw_graph,
        file_language_map,
        edge_specifier_map,
    )

    limitations: list[str] = []

    # Report unverified edges as limitations
    if report.unverified > 0:
        unverified_reasons = [r.reason for r in report.results if r.status == 'unverified']
        limitations.append(
            f'{report.unverified} edge(s) failed verification and were removed: '
            + '; '.join(unverified_reasons[:5])
            + (f' (and {len(unverified_reasons) - 5} more)' if len(unverified_reasons) > 5 else '')
        )

    # Summarise unresolved references
    bare_count = sum(1 for u in verified_graph.unresolved if u.reason == 'bare_package')
    not_found_count = sum(1 for u in verified_graph.unresolved if u.reason == 'not_found')
    if bare_count:
        limitations.append(
            f'{bare_count} import(s) are bare package references (external dependencies); '
            'no in-snapshot edge is drawn.'
        )
    if not_found_count:
        limitations.append(
            f'{not_found_count} import(s) could not be resolved to a file in this snapshot; '
            'they are listed as unresolved references.'
        )

    # Change impact
    all_file_paths = {r.path for r in get_inventory(snapshot_id, limit=None).files if not r.excluded}
    affected: list[str] = []
    truncated = False

    if path is None or path == '.':
        # No meaningful subject — disclose rather than return a silent empty list.
        limitations.append(
            'Change impact requires a specific file or folder to be selected; '
            'select a file or folder to see which other files would be affected.'
        )
    else:
        # Resolve subject to the set of paths it covers.
        if path in all_file_paths:
            subject_paths: set[str] = {path}
        else:
            prefix = path.rstrip('/') + '/'
            subject_paths = {p for p in all_file_paths if p == path or p.startswith(prefix)}

        if subject_paths >= all_file_paths:
            # Subject covers the whole repository — same as the no-subject case.
            limitations.append(
                'Change impact requires a specific file or folder to be selected; '
                'select a file or folder to see which other files would be affected.'
            )
        else:
            affected, truncated = compute_impact(snapshot_id, verified_graph, path)
            if truncated:
                limitations.append(
                    f'Change impact walk capped at {IMPACT_WALK_CAP} files; '
                    'actual affected count may be higher.'
                )

    return DependencyOverlay(
        snapshot_id=snapshot_id,
        graph=verified_graph,
        impact_subject_ids=affected,
        limitations=limitations,
    )


async def build_dependencies(snapshot_id: str, path: str | None, depth: int | None) -> DependencyOverlay:
    return await asyncio.to_thread(_build_dependencies, snapshot_id, path, depth)
