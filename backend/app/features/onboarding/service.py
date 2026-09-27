"""Proposals and change packs.

The other slots answer questions about a repository as it is. This one answers
the question that follows: given something you are about to change, what else
has to change with it, and what do we not know yet?

Every proposal is derived from facts another slot already verified. A proposal
is never a suggestion to go read something; it is a statement that a specific
file, at a specific line range, causes a specific set of other files to be
affected. Anything that cannot be established from the snapshot is returned in
`limitations` rather than inferred.

The rule, as everywhere else in this codebase: report the truth, disclose the
limit. A proposal with no evidence behind it is not a proposal.
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from app.features.dependencies.service import (
    DependencyGraph,
    build_dependencies,
    compute_impact,
)
from app.services.snapshot_service import get_inventory
from app.services.v1_errors import WorkspaceError


class ProposalEvidence(BaseModel):
    """A source range a proposal is derived from."""

    file_id: str
    path: str
    line_start: int
    line_end: int
    content_sha256: str


class Proposal(BaseModel):
    """One proposed change, with the evidence it rests on."""

    id: str
    kind: str
    title: str
    detail: str
    subject_path: str
    affected_paths: list[str]
    affected_count: int
    impact_truncated: bool
    evidence: list[ProposalEvidence]
    limitations: list[str] = Field(default_factory=list)


class ProposalsResponse(BaseModel):
    """Response contract for the proposals slot."""

    schema_version: str = '1.1'
    snapshot_id: str
    proposals: list[Proposal]
    limitations: list[str]


def _high_degree_subjects(graph: DependencyGraph, limit: int) -> list[str]:
    """Files that the most other files depend on, highest first."""
    incoming: dict[str, int] = {}
    for edge in graph.edges:
        if edge.target.path:
            incoming[edge.target.path] = incoming.get(edge.target.path, 0) + 1
    ordered = sorted(incoming.items(), key=lambda item: (-item[1], item[0]))
    return [path for path, _ in ordered[:limit]]


def _importing_files(graph: DependencyGraph, path: str) -> list[str]:
    """Source paths of verified edges that import the given path."""
    return sorted(
        {edge.source.path for edge in graph.edges if edge.target.path == path and edge.source.path}
    )


def _evidence_for(graph: DependencyGraph, path: str, cap: int = 4) -> list[ProposalEvidence]:
    """Citation ranges for the edges pointing at this subject."""
    evidence: list[ProposalEvidence] = []
    for edge in graph.edges:
        if edge.target.path != path:
            continue
        item = next((e for e in graph.evidence if e.id == edge.evidence_id), None)
        if item is None:
            continue
        evidence.append(
            ProposalEvidence(
                file_id=item.file_id,
                path=item.path,
                line_start=item.range.line_start,
                line_end=item.range.line_end,
                content_sha256=item.content_sha256,
            )
        )
        if len(evidence) >= cap:
            break
    return evidence


async def build_proposals(snapshot_id: str, subject: str | None = None) -> ProposalsResponse:
    """Build change proposals for a snapshot, or for one subject path."""
    inventory = get_inventory(snapshot_id, limit=None)
    if not inventory.files:
        raise WorkspaceError('NOT_FOUND', 'This snapshot has no files to propose changes for.', 404)

    overlay = await build_dependencies(snapshot_id, subject, None)
    graph = overlay.graph
    limitations = list(overlay.limitations)

    if not graph.edges:
        limitations.append(
            'No verified import edge exists in this snapshot, so no change proposal can be '
            'derived. This is a coverage limit, not an absence of coupling.'
        )
        return ProposalsResponse(
            snapshot_id=snapshot_id, proposals=[], limitations=limitations
        )

    if subject is not None:
        subjects = [subject]
    else:
        subjects = _high_degree_subjects(graph, limit=5)

    proposals: list[Proposal] = []

    for path in subjects:
        affected_ids, truncated = compute_impact(snapshot_id, graph, path)
        affected_paths = sorted(
            {record.path for record in inventory.files if record.id in set(affected_ids)}
        )
        importers = _importing_files(graph, path)
        evidence = _evidence_for(graph, path)

        if affected_paths:
            detail = (
                f'{path} is transitively imported by {len(affected_paths)} other file(s). '
                f'Changing it changes what those files resolve to at import time.'
            )
            kind = 'change_impact'
        else:
            detail = (
                f'{path} is imported by {len(importers)} file(s), but none of them appear in a '
                f'reverse dependency walk, so no downstream file is provably affected today. '
                f'This is a statement about the verified graph, not a guarantee that nothing breaks.'
            )
            kind = 'review_first'

        item_limitations: list[str] = []
        if truncated:
            item_limitations.append(
                'The impact walk was capped, so this count is a lower bound rather than the '
                'full affected set.'
            )
        if not evidence:
            item_limitations.append(
                'No citation backs this proposal, so it is offered for review rather than as a '
                'verified consequence.'
            )

        proposals.append(
            Proposal(
                id=f'proposal_{abs(hash((snapshot_id, path))) % (10**12):012d}',
                kind=kind,
                title=f'Review before changing {path}',
                detail=detail,
                subject_path=path,
                affected_paths=affected_paths,
                affected_count=len(affected_paths),
                impact_truncated=truncated,
                evidence=evidence,
                limitations=item_limitations,
            )
        )

    if subject is None and len(subjects) < 5:
        limitations.append(
            f'Only {len(subjects)} subject(s) had enough incoming edges to rank. Additional files '
            f'are imported by nothing in the verified graph and carry no proposal.'
        )

    return ProposalsResponse(
        snapshot_id=snapshot_id, proposals=proposals, limitations=limitations
    )


__all__ = ['ProposalsResponse', 'Proposal', 'ProposalEvidence', 'build_proposals']
