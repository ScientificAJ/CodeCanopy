"""Tests for the summary verifier.

Covers:
- verified result for a correctly cited range
- unverified when line_end > total_lines (out of bounds)
- unverified when content hash is wrong
- unverified when file_id belongs to a different snapshot
- unverified when line_start < 1
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.features.summaries.service import EvidenceItem, SourceRange, SummaryPayload, build_summary
from app.features.summaries.verifier import VerificationReport, verify_evidence
from app.services.snapshot_service import create_snapshot_from_project, get_inventory


def make_snapshot(tmp_path, monkeypatch, files: dict[str, str]):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    source = tmp_path / 'source'
    source.mkdir()
    for name, text in files.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    snap, _ = create_snapshot_from_project('a' * 32, source, 'test', 'test-project')
    return snap


def _make_payload(snapshot_id: str, evidence: list[EvidenceItem]) -> SummaryPayload:
    return SummaryPayload(
        snapshot_id=snapshot_id,
        entity_id='test-entity',
        text='test summary',
        evidence=evidence,
        limitations=[],
    )


def _get_record(snap_id, path):
    records = get_inventory(snap_id, limit=100).files
    return next(r for r in records if r.path == path)


# ---------------------------------------------------------------------------

def test_valid_range_is_verified(tmp_path, monkeypatch):
    code = 'def hello():\n    return 1\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'f.py': code})
    rec = _get_record(snap.id, 'f.py')

    ev = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec.id,
        path=rec.path,
        range=SourceRange(line_start=1, line_end=2),
        content_sha256=rec.content_hash,
        basis='observed',
    )
    report = verify_evidence(snap.id, _make_payload(snap.id, [ev]))
    assert report.verified == 1
    assert report.unverified == 0


def test_out_of_bounds_line_end_is_unverified(tmp_path, monkeypatch):
    snap = make_snapshot(tmp_path, monkeypatch, {'f.py': 'x = 1\n'})
    rec = _get_record(snap.id, 'f.py')

    ev = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec.id,
        path=rec.path,
        range=SourceRange(line_start=1, line_end=500),  # way past end
        content_sha256=rec.content_hash,
        basis='observed',
    )
    report = verify_evidence(snap.id, _make_payload(snap.id, [ev]))
    assert report.unverified == 1
    assert report.results[0].reason is not None


def test_wrong_hash_is_unverified(tmp_path, monkeypatch):
    snap = make_snapshot(tmp_path, monkeypatch, {'f.py': 'x = 1\n'})
    rec = _get_record(snap.id, 'f.py')

    ev = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec.id,
        path=rec.path,
        range=SourceRange(line_start=1, line_end=1),
        content_sha256='0' * 64,  # wrong hash
        basis='observed',
    )
    report = verify_evidence(snap.id, _make_payload(snap.id, [ev]))
    assert report.unverified == 1
    assert 'hash' in report.results[0].reason.lower()


def test_invalid_line_start_is_unverified(tmp_path, monkeypatch):
    snap = make_snapshot(tmp_path, monkeypatch, {'f.py': 'x = 1\n'})
    rec = _get_record(snap.id, 'f.py')

    ev = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec.id,
        path=rec.path,
        range=SourceRange(line_start=0, line_end=1),  # invalid: must be >= 1
        content_sha256=rec.content_hash,
        basis='observed',
    )
    report = verify_evidence(snap.id, _make_payload(snap.id, [ev]))
    assert report.unverified == 1


def test_file_id_from_different_snapshot_is_rejected(tmp_path, monkeypatch):
    snap1 = make_snapshot(tmp_path, monkeypatch, {'a.py': 'x = 1\n'})
    # Create a second distinct snapshot
    source2 = tmp_path / 'src2'
    source2.mkdir()
    (source2 / 'b.py').write_text('y = 2\n', encoding='utf-8')
    snap2, _ = create_snapshot_from_project('b' * 32, source2, 'test2', 'proj2')

    snap2_rec = _get_record(snap2.id, 'b.py')

    # Evidence says it's in snap1 but uses a file_id from snap2
    ev = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap1.id,
        file_id=snap2_rec.id,
        path='b.py',
        range=SourceRange(line_start=1, line_end=1),
        content_sha256=snap2_rec.content_hash,
        basis='observed',
    )
    report = verify_evidence(snap1.id, _make_payload(snap1.id, [ev]))
    assert report.unverified == 1


def test_empty_evidence_gives_zero_counts(tmp_path, monkeypatch):
    snap = make_snapshot(tmp_path, monkeypatch, {'f.py': 'x = 1\n'})
    payload = _make_payload(snap.id, [])
    report = verify_evidence(snap.id, payload)
    assert report.verified == 0
    assert report.unverified == 0


def test_all_evidence_from_real_summary_is_verified(tmp_path, monkeypatch):
    """End-to-end: build a summary then verify all its citations."""
    code = '"""Module.\n"""\ndef work():\n    pass\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'work.py': code})
    payload = asyncio.run(build_summary(snap.id, 'work.py'))
    report = verify_evidence(snap.id, payload)
    assert report.unverified == 0, [r for r in report.results if r.status == 'unverified']
