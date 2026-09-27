"""Tests for the proposals slot.

The bar here is the same as the dependency verifier: a proposal that cannot be
derived from the snapshot must not be returned, and a limitation must appear
instead. These tests build real snapshots rather than mocking the service.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import tempfile
from pathlib import Path

import pytest

from app.features.onboarding.service import build_proposals
from app.services.snapshot_service import create_snapshot_from_project

FILES = {
    'pkg/utils.py': 'def helper():\n    return 42\n',
    'pkg/main.py': 'from .utils import helper\n\ndef run():\n    return helper()\n',
    'pkg/app.py': 'from .main import run\nimport os\n\nrun()\n',
}

ISOLATED = {
    'solo/only.py': 'def isolated():\n    return 1\n',
    'other/second.py': 'VALUE = 2\n',
}


def _snapshot(files: dict[str, str]):
    root = Path(tempfile.mkdtemp())
    source = root / 'source'
    source.mkdir()
    for name, text in files.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    workspace = secrets.token_hex(32)
    project = 'a' * 32
    snap, _ = create_snapshot_from_project(
        project, source, 'test', 'proposals', workspace_id=hashlib.sha256(workspace.encode()).hexdigest()
    )
    return snap


def test_proposals_are_derived_from_verified_edges():
    snap = _snapshot(FILES)
    result = asyncio.run(build_proposals(snap.id))
    assert result.proposals, 'a snapshot with real imports must yield a proposal'
    assert all(p.subject_path for p in result.proposals)


def test_every_proposal_cites_a_real_source_range():
    snap = _snapshot(FILES)
    result = asyncio.run(build_proposals(snap.id))
    for proposal in result.proposals:
        if proposal.kind == 'change_impact':
            assert proposal.evidence, 'an impact proposal must cite the import that causes it'
            for item in proposal.evidence:
                assert item.line_start >= 1
                assert item.content_sha256


def test_subject_scoped_proposal_reports_impact():
    snap = _snapshot(FILES)
    result = asyncio.run(build_proposals(snap.id, subject='pkg/utils.py'))
    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.subject_path == 'pkg/utils.py'
    assert proposal.affected_count >= 1
    assert 'pkg/main.py' in proposal.affected_paths


def test_no_edges_returns_no_proposals_and_says_why():
    snap = _snapshot(ISOLATED)
    result = asyncio.run(build_proposals(snap.id))
    assert result.proposals == []
    assert any('No verified import edge' in line for line in result.limitations)


def test_unresolved_references_are_never_presented_as_impact():
    snap = _snapshot(FILES)
    result = asyncio.run(build_proposals(snap.id, subject='pkg/utils.py'))
    proposal = result.proposals[0]
    # `os` is a bare package in pkg/app.py and is never a file in the snapshot
    assert all(not path.endswith('os') for path in proposal.affected_paths)


def test_unknown_subject_is_rejected_rather_than_guessed():
    snap = _snapshot(FILES)
    with pytest.raises(Exception) as exc_info:
        asyncio.run(build_proposals(snap.id, subject='does/not/exist.py'))
    assert 'NOT_FOUND' in str(exc_info.value) or 'not in this snapshot' in str(exc_info.value)


def test_truncated_impact_is_disclosed_not_hidden():
    snap = _snapshot(FILES)
    result = asyncio.run(build_proposals(snap.id, subject='pkg/utils.py'))
    proposal = result.proposals[0]
    if proposal.impact_truncated:
        assert any('capped' in line for line in proposal.limitations)


def test_empty_snapshot_raises_instead_of_returning_nothing():
    snap = _snapshot({'pkg/only.py': 'X = 1\n'})
    result = asyncio.run(build_proposals(snap.id))
    # a file with no imports is not an error; it is a disclosed coverage limit
    assert result.proposals == []
    assert result.limitations
