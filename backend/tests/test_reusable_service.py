"""Tests for ConcreteReusableFunctionService cross-file reuse detection."""
import asyncio
import json

from app.features.reusable_functions import (
    ConcreteReusableFunctionService,
    ReusableFunctionRequest,
)


def _write_snapshot(tmp_path, snapshot_id: str, syntax: dict) -> None:
    snap_dir = tmp_path / snapshot_id
    snap_dir.mkdir(parents=True)
    snap_json = {
        "id": snapshot_id,
        "project_id": "proj_" + snapshot_id,
        "source": {"kind": "zip", "archive_digest": "abc", "display_ref": "test"},
        "manifest_hash": "abc123",
        "created_at": "2099-01-01T00:00:00+00:00",
        "expires_at": "2099-12-31T00:00:00+00:00",
        "analysis_run_id": None,
    }
    (snap_dir / "snapshot.json").write_text(json.dumps(snap_json), encoding="utf-8")
    (snap_dir / "syntax.json").write_text(json.dumps(syntax), encoding="utf-8")


def test_cross_file_reuse_detected(tmp_path, monkeypatch):
    monkeypatch.setenv("CODECANOPY_SNAPSHOTS_DIR", str(tmp_path))
    snapshot_id = "a" * 32

    syntax = {
        "id_file_a": {
            "path": "path/to/a.py",
            "functions": [{"name": "helper", "file": "path/to/a.py", "line_start": 1, "line_end": 2}],
            "call_sites": [],
        },
        "id_file_b": {
            "path": "path/to/b.py",
            "functions": [],
            "call_sites": [{"callee_name": "helper", "file": "path/to/b.py", "line_start": 5, "line_end": 5}],
        },
    }
    _write_snapshot(tmp_path, snapshot_id, syntax)

    service = ConcreteReusableFunctionService()
    result = asyncio.run(service.execute(ReusableFunctionRequest(snapshot_id=snapshot_id, min_callers=1)))

    assert result.snapshot_id == snapshot_id
    assert result.total_reusable == 1
    assert result.groups[0].function_name == "helper"
    assert result.groups[0].defined_in == "path/to/a.py"
    assert "path/to/b.py" in result.groups[0].called_from


def test_same_file_caller_excluded(tmp_path, monkeypatch):
    """A function called only from the same file it's defined in is NOT reusable."""
    monkeypatch.setenv("CODECANOPY_SNAPSHOTS_DIR", str(tmp_path))
    snapshot_id = "b" * 32

    syntax = {
        "id_file_a": {
            "path": "utils.py",
            "functions": [{"name": "helper", "file": "utils.py", "line_start": 1, "line_end": 2}],
            "call_sites": [{"callee_name": "helper", "file": "utils.py", "line_start": 10, "line_end": 10}],
        },
    }
    _write_snapshot(tmp_path, snapshot_id, syntax)

    service = ConcreteReusableFunctionService()
    result = asyncio.run(service.execute(ReusableFunctionRequest(snapshot_id=snapshot_id, min_callers=1)))

    assert result.total_reusable == 0


def test_min_callers_threshold(tmp_path, monkeypatch):
    """min_callers=2 requires at least two distinct caller files."""
    monkeypatch.setenv("CODECANOPY_SNAPSHOTS_DIR", str(tmp_path))
    snapshot_id = "c" * 32

    syntax = {
        "id_a": {
            "path": "lib.py",
            "functions": [{"name": "util", "file": "lib.py", "line_start": 1, "line_end": 1}],
            "call_sites": [],
        },
        "id_b": {
            "path": "caller1.py",
            "functions": [],
            "call_sites": [{"callee_name": "util", "file": "caller1.py", "line_start": 3, "line_end": 3}],
        },
    }
    _write_snapshot(tmp_path, snapshot_id, syntax)

    service = ConcreteReusableFunctionService()
    result = asyncio.run(service.execute(ReusableFunctionRequest(snapshot_id=snapshot_id, min_callers=2)))

    assert result.total_reusable == 0


def test_missing_syntax_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CODECANOPY_SNAPSHOTS_DIR", str(tmp_path))
    snapshot_id = "d" * 32

    snap_dir = tmp_path / snapshot_id
    snap_dir.mkdir()
    snap_json = {
        "id": snapshot_id,
        "project_id": "proj_x",
        "source": {"kind": "zip", "archive_digest": "x", "display_ref": "test"},
        "manifest_hash": "x",
        "created_at": "2099-01-01T00:00:00+00:00",
        "expires_at": "2099-12-31T00:00:00+00:00",
        "analysis_run_id": None,
    }
    (snap_dir / "snapshot.json").write_text(json.dumps(snap_json), encoding="utf-8")

    service = ConcreteReusableFunctionService()
    result = asyncio.run(service.execute(ReusableFunctionRequest(snapshot_id=snapshot_id, min_callers=1)))

    assert result.total_reusable == 0
    assert result.groups == []
