"""Tests for the Ask CodeCanopy slot endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.main import app
from test_v1_workspace import client, import_files  # noqa: F401


# ---------------------------------------------------------------------------
# Slot endpoint returns 200 and is no longer NOT_CONNECTED
# ---------------------------------------------------------------------------

def test_ask_slot_returns_200_when_key_is_set(client, monkeypatch):  # noqa: F811
    monkeypatch.setenv('GROQ_API_KEY', 'test-key-for-slot-check')
    path, _, _ = import_files(client, {'src/app.py': 'def hello(): pass\n'})
    response = client.get(path + '/ask')
    assert response.status_code == 200, response.text
    body = response.json()
    # Must not be the NOT_CONNECTED slot stub
    assert 'status' not in body or body.get('status') != 'NOT_CONNECTED'
    # Must contain the AskResponse fields with a real, non-empty answer
    assert 'answer' in body
    assert 'context_hint' in body
    # The answer must be real content — not empty, not whitespace, not a placeholder
    assert body['answer'].strip(), "answer must not be empty or whitespace"
    assert len(body['answer']) > 20, "answer must be a real description, not a token"
    assert body['answer'] != '""', "answer must not be a quoted empty string"
    # No secret must appear in the response body
    assert 'GROQ_API_KEY' not in body['answer']
    assert 'Bearer ' not in body['answer']


def test_ask_slot_returns_503_when_key_is_absent(client, monkeypatch):  # noqa: F811
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    path, _, _ = import_files(client, {'src/app.py': 'x = 1\n'})
    response = client.get(path + '/ask')
    assert response.status_code == 503, response.text
    body = response.json()
    # Real error message — not a generic placeholder
    assert 'GROQ_API_KEY' in body.get('detail', '') or 'AI_NOT_CONFIGURED' in str(body)


def test_ask_slot_context_hint_references_snapshot(client, monkeypatch):  # noqa: F811
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    path, run, _ = import_files(client, {'readme.md': '# Hello\n'})
    response = client.get(path + '/ask')
    assert response.status_code == 200
    body = response.json()
    snapshot_id = run['result_snapshot_id']
    assert snapshot_id in body['context_hint']


def test_ask_slot_requires_valid_session(monkeypatch, tmp_path):
    """Slot must reject unauthenticated callers — same as other slot endpoints."""
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    with TestClient(app) as stranger:
        # No session established — bogus path returns 4xx not 200
        response = stranger.get('/api/v1/projects/no-project/snapshots/no-snap/ask')
        assert response.status_code in (401, 403, 404)
