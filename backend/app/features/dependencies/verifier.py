"""Dependency edge verifier.

Each edge's cited line is re-read through read_source_lines and
checked for:
  0. The target file_id resolves to a real file in this snapshot.
  1. The source file_id resolves in this snapshot (not another).
  2. The range is valid (line_start >= 1, line_end >= line_start).
  3. The range is within the file's real line count.
  4. The content hash matches the snapshot record.
  5. The cited line actually contains an import statement naming the
     target specifier  (the extra guard that catches false edges
     pointing at a real but unrelated line).

Edges that fail any guard are removed from the graph and their
evidence_ids are listed in limitations.  They are never drawn faintly.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.features.dependencies.service import (
    DependencyEdge,
    DependencyGraph,
    EvidenceItem,
)
from app.services.snapshot_service import get_file_record, read_source_lines
from app.services.v1_errors import WorkspaceError


class EdgeVerificationResult(BaseModel):
    edge_id: str
    status: str        # 'verified' | 'unverified'
    reason: str | None = None


class DependencyVerificationReport(BaseModel):
    snapshot_id: str
    verified: int
    unverified: int
    results: list[EdgeVerificationResult]


def _line_contains_import(line: str, specifier: str, language: str) -> bool:
    """Return True if `line` contains an import statement naming `specifier`."""
    if language in ('javascript', 'typescript'):
        escaped = re.escape(specifier)
        return bool(re.search(r'\b(?:import|require)\b', line) and re.search(escaped, line))
    # Python
    escaped = re.escape(specifier)
    return bool(re.search(r'^\s*(?:from|import)\s+', line) and re.search(escaped, line))


def verify_dependency_edges(
    snapshot_id: str,
    graph: DependencyGraph,
    source_language_map: dict[str, str],  # file_id → language
    edge_specifier_map: dict[str, str],   # edge_id → original specifier
) -> tuple[DependencyGraph, DependencyVerificationReport]:
    """Verify every edge in the graph.

    Returns a new graph containing only verified edges plus a report.
    Unverified edges are removed (not drawn).
    """
    evidence_by_id: dict[str, EvidenceItem] = {ev.id: ev for ev in graph.evidence}

    results: list[EdgeVerificationResult] = []
    verified_edge_ids: set[str] = set()

    for edge in graph.edges:
        # Guard 0: target file_id must name a real file in this snapshot
        tgt_file_id = edge.target.file_id
        if tgt_file_id is None:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=(
                    f'Target endpoint for edge {edge.id!r} has no file_id '
                    f'(external or unresolved target).'
                ),
            ))
            continue
        try:
            get_file_record(snapshot_id, tgt_file_id)
        except WorkspaceError:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=(
                    f'Target file_id {tgt_file_id!r} (path {edge.target.path!r}) '
                    f'not found in snapshot {snapshot_id!r}.'
                ),
            ))
            continue

        ev_id = edge.evidence_id
        if ev_id is None:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason='Edge has no evidence item.',
            ))
            continue

        ev = evidence_by_id.get(ev_id)
        if ev is None:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=f'Evidence item {ev_id!r} not found in graph.',
            ))
            continue

        # Guard 1: file_id must belong to this snapshot
        try:
            rec = get_file_record(snapshot_id, ev.file_id)
        except WorkspaceError as err:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=f'file_id {ev.file_id!r} not found in snapshot {snapshot_id!r}: {err.message}',
            ))
            continue

        # Guard 2: range sanity
        ls, le = ev.range.line_start, ev.range.line_end
        if ls < 1 or le < ls:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=f'Invalid range: line_start={ls}, line_end={le}.',
            ))
            continue

        # Guard 3+4: read range and check bounds and hash
        try:
            sl = read_source_lines(snapshot_id, ev.file_id, ls, le, max_lines=2000)
        except WorkspaceError as err:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=f'Range [{ls}–{le}] unreadable: {err.message}',
            ))
            continue

        if le > sl.total_lines:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=(
                    f'line_end {le} exceeds file length {sl.total_lines} '
                    f'for {ev.path!r}.'
                ),
            ))
            continue

        if sl.content_hash != ev.content_sha256:
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=(
                    f'Content hash mismatch for {ev.path!r}: '
                    f'expected {ev.content_sha256!r}, got {sl.content_hash!r}.'
                ),
            ))
            continue

        # Guard 5: the cited line must actually contain an import naming the target
        specifier = edge_specifier_map.get(edge.id, '')
        language = source_language_map.get(ev.file_id, rec.language)
        cited_content = sl.content  # content of the cited range
        first_line = cited_content.split('\n')[0] if cited_content else ''
        if specifier and not _line_contains_import(first_line, specifier, language):
            results.append(EdgeVerificationResult(
                edge_id=edge.id,
                status='unverified',
                reason=(
                    f'Cited line {ls} of {ev.path!r} does not contain an '
                    f'import of {specifier!r}.'
                ),
            ))
            continue

        results.append(EdgeVerificationResult(edge_id=edge.id, status='verified'))
        verified_edge_ids.add(edge.id)

    verified_count = sum(1 for r in results if r.status == 'verified')
    unverified_count = len(results) - verified_count

    # Build pruned graph: keep only verified edges and their evidence
    verified_edges = [e for e in graph.edges if e.id in verified_edge_ids]
    used_evidence_ids = {e.evidence_id for e in verified_edges if e.evidence_id}
    verified_evidence = [ev for ev in graph.evidence if ev.id in used_evidence_ids]

    pruned_graph = DependencyGraph(
        edges=verified_edges,
        unresolved=graph.unresolved,
        evidence=verified_evidence,
    )

    report = DependencyVerificationReport(
        snapshot_id=snapshot_id,
        verified=verified_count,
        unverified=unverified_count,
        results=results,
    )

    return pruned_graph, report
