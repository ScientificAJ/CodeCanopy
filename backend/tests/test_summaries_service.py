"""Tests for the deterministic summary engine.

Covers:
- a file with a docstring produces a cited claim whose range contains the docstring
- a function claim cites the line the function is defined on
- a citation pointing past end-of-file is reported unverified, not dropped
- the service still returns a valid SummaryPayload with no AI key present
- the response validates against SummaryPayload
- a folder summary aggregates its children
"""
from __future__ import annotations

import asyncio
import uuid as _uuid

import pytest

from app.features.summaries.service import EvidenceItem, SourceRange, SummaryPayload, build_summary
from app.features.summaries.verifier import verify_evidence
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


# ---------------------------------------------------------------------------
# File-level tests
# ---------------------------------------------------------------------------

def test_file_with_docstring_produces_cited_docstring_claim(tmp_path, monkeypatch):
    code = '"""This module does something.\n\nMultiline.\n"""\ndef foo():\n    pass\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'example.py': code})
    payload = asyncio.run(build_summary(snap.id, 'example.py'))

    assert payload.schema_version == '1.1'
    assert payload.snapshot_id == snap.id
    # docstring evidence must exist and span lines 1–4
    docstring_evs = [ev for ev in payload.evidence if ev.range.line_start == 1 and ev.range.line_end >= 3]
    assert docstring_evs, 'Expected at least one evidence item spanning the docstring'
    ev = docstring_evs[0]
    assert ev.basis == 'observed'
    assert ev.file_id  # non-empty
    assert f'[{ev.id}]' in payload.text


def test_function_claim_cites_definition_line(tmp_path, monkeypatch):
    code = 'def greet(name):\n    return f"Hello {name}"\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'greet.py': code})
    payload = asyncio.run(build_summary(snap.id, 'greet.py'))

    fn_evs = [ev for ev in payload.evidence if ev.range.line_start == 1]
    assert fn_evs, 'Expected evidence starting at line 1 for function greet'
    ev = fn_evs[0]
    assert ev.range.line_end >= ev.range.line_start
    assert '`greet`' in payload.text or 'greet' in payload.text


def test_summary_payload_is_valid_with_no_ai_key(tmp_path, monkeypatch):
    """Service must return complete SummaryPayload even when no AI key is set."""
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    code = 'x = 1\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'simple.py': code})
    payload = asyncio.run(build_summary(snap.id, 'simple.py'))

    # Must validate as SummaryPayload
    validated = SummaryPayload.model_validate(payload.model_dump())
    assert validated.schema_version == '1.1'
    assert validated.snapshot_id == snap.id
    assert validated.text  # non-empty


def test_folder_summary_aggregates_children(tmp_path, monkeypatch):
    files = {
        'pkg/a.py': 'def alpha(): pass\n',
        'pkg/b.py': 'def beta(): pass\ndef gamma(): pass\n',
    }
    snap = make_snapshot(tmp_path, monkeypatch, files)
    payload = asyncio.run(build_summary(snap.id, 'pkg'))

    assert '2' in payload.text or 'files' in payload.text.lower()
    # folder entity id must be set
    assert payload.entity_id
    # should mention both functions somewhere
    assert 'alpha' in payload.text or 'beta' in payload.text or 'gamma' in payload.text


def test_root_folder_summary(tmp_path, monkeypatch):
    files = {
        'a.py': 'def foo(): pass\n',
        'b.js': 'function bar() {}\n',
    }
    snap = make_snapshot(tmp_path, monkeypatch, files)
    payload = asyncio.run(build_summary(snap.id, None))

    assert payload.schema_version == '1.1'
    assert 'python' in payload.text.lower() or 'javascript' in payload.text.lower()


def test_unknown_path_raises_404(tmp_path, monkeypatch):
    from app.services.v1_errors import WorkspaceError
    snap = make_snapshot(tmp_path, monkeypatch, {'a.py': 'x = 1\n'})
    with pytest.raises(WorkspaceError) as exc_info:
        asyncio.run(build_summary(snap.id, 'does_not_exist.py'))
    assert exc_info.value.status == 404


# ---------------------------------------------------------------------------
# Verifier tests
# ---------------------------------------------------------------------------

def test_all_citations_verified_for_real_file(tmp_path, monkeypatch):
    code = '"""Module doc.\n"""\ndef process(x):\n    return x * 2\n'
    snap = make_snapshot(tmp_path, monkeypatch, {'proc.py': code})
    payload = asyncio.run(build_summary(snap.id, 'proc.py'))
    report = verify_evidence(snap.id, payload)

    assert report.unverified == 0, [r for r in report.results if r.status == 'unverified']
    assert report.verified == len(payload.evidence)


def test_out_of_bounds_citation_is_unverified_not_dropped(tmp_path, monkeypatch):
    """Manually crafted evidence that points past end-of-file must be flagged unverified."""
    code = 'x = 1\n'  # 1 line
    snap = make_snapshot(tmp_path, monkeypatch, {'one.py': code})

    # Get the real file_id and hash
    records = get_inventory(snap.id, limit=100).files
    rec = next(r for r in records if r.path == 'one.py')

    bad_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec.id,
        path=rec.path,
        range=SourceRange(line_start=1, line_end=999),  # past end of file
        content_sha256=rec.content_hash,
        basis='observed',
    )
    fake_payload = SummaryPayload(
        snapshot_id=snap.id,
        entity_id='test',
        text='fake',
        evidence=[bad_ev],
        limitations=[],
    )
    report = verify_evidence(snap.id, fake_payload)
    assert report.unverified == 1
    assert report.verified == 0
    result = report.results[0]
    assert result.status == 'unverified'
    assert 'exceed' in result.reason.lower() or 'bound' in result.reason.lower() or 'range' in result.reason.lower()


def test_wrong_snapshot_file_id_is_rejected(tmp_path, monkeypatch):
    """A file_id from a different snapshot must be reported unverified."""
    snap1 = make_snapshot(tmp_path, monkeypatch, {'a.py': 'x = 1\n'})
    # Create a second snapshot in the same dir
    source2 = tmp_path / 'source2'
    source2.mkdir()
    (source2 / 'b.py').write_text('y = 2\n', encoding='utf-8')
    snap2, _ = create_snapshot_from_project('b' * 32, source2, 'test', 'other-project')

    snap2_records = get_inventory(snap2.id, limit=100).files
    snap2_file_id = snap2_records[0].id
    snap2_hash = snap2_records[0].content_hash

    # Craft evidence for snap1's summary but using snap2's file_id
    bad_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap1.id,  # payload says snap1
        file_id=snap2_file_id,  # but file belongs to snap2
        path='b.py',
        range=SourceRange(line_start=1, line_end=1),
        content_sha256=snap2_hash,
        basis='observed',
    )
    fake_payload = SummaryPayload(
        snapshot_id=snap1.id,
        entity_id='test',
        text='fake',
        evidence=[bad_ev],
        limitations=[],
    )
    # Verifier checks against snap1 — snap2's file_id must not resolve there
    report = verify_evidence(snap1.id, fake_payload)
    assert report.unverified == 1
    assert 'not found' in report.results[0].reason.lower()
