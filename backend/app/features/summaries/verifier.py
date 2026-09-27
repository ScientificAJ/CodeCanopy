"""Verifier: re-reads every evidence item through read_source_lines and
confirms the cited range is within bounds and the file hash matches.

Verification is independent of summary generation — it makes no
assumptions about how the evidence was produced.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.features.summaries.service import EvidenceItem, SummaryPayload
from app.services.snapshot_service import get_file_record, read_source_lines
from app.services.v1_errors import WorkspaceError


class VerificationResult(BaseModel):
    evidence_id: str
    status: str          # 'verified' | 'unverified'
    reason: str | None = None


class VerificationReport(BaseModel):
    snapshot_id: str
    verified: int
    unverified: int
    results: list[VerificationResult]


def verify_evidence(snapshot_id: str, payload: SummaryPayload) -> VerificationReport:
    """Independently verify each evidence item in a SummaryPayload.

    For each item the verifier checks:
      1. The file_id resolves in *this* snapshot (not another).
      2. line_start >= 1 and line_end >= line_start.
      3. The range is within the file's real line count.
      4. The content hash from the snapshot record equals evidence.content_sha256.

    Any claim that cannot be confirmed is reported as 'unverified' with a
    reason string.  The caller should move such claims to `limitations`.
    """
    results: list[VerificationResult] = []

    for ev in payload.evidence:
        # Guard 1: snapshot scope — the file_id must belong to *this* snapshot
        try:
            rec = get_file_record(snapshot_id, ev.file_id)
        except WorkspaceError as err:
            results.append(VerificationResult(
                evidence_id=ev.id,
                status='unverified',
                reason=f'file_id {ev.file_id!r} not found in snapshot {snapshot_id!r}: {err.message}',
            ))
            continue

        # Guard 2: range sanity
        ls, le = ev.range.line_start, ev.range.line_end
        if ls < 1 or le < ls:
            results.append(VerificationResult(
                evidence_id=ev.id,
                status='unverified',
                reason=f'Invalid range: line_start={ls}, line_end={le}.',
            ))
            continue

        # Guard 3 + 4: read the range and check bounds and hash
        try:
            sl = read_source_lines(snapshot_id, ev.file_id, ls, le, max_lines=2000)
        except WorkspaceError as err:
            results.append(VerificationResult(
                evidence_id=ev.id,
                status='unverified',
                reason=f'Range [{ls}–{le}] unreadable: {err.message}',
            ))
            continue

        if le > sl.total_lines:
            results.append(VerificationResult(
                evidence_id=ev.id,
                status='unverified',
                reason=(
                    f'line_end {le} exceeds file length {sl.total_lines} '
                    f'for {ev.path!r}.'
                ),
            ))
            continue

        if sl.content_hash != ev.content_sha256:
            results.append(VerificationResult(
                evidence_id=ev.id,
                status='unverified',
                reason=(
                    f'Content hash mismatch for {ev.path!r}: '
                    f'expected {ev.content_sha256!r}, got {sl.content_hash!r}.'
                ),
            ))
            continue

        results.append(VerificationResult(evidence_id=ev.id, status='verified'))

    verified = sum(1 for r in results if r.status == 'verified')
    return VerificationReport(
        snapshot_id=snapshot_id,
        verified=verified,
        unverified=len(results) - verified,
        results=results,
    )
