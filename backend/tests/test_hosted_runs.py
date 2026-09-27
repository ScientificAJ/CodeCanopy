"""Hosted work cannot depend on a warm process or detached worker lifetime."""
import threading
import uuid

import pytest

from app.models.v1.snapshot import RunStatus
from app.services import run_service
from app.services.v1_errors import WorkspaceError


@pytest.fixture
def hosted_runs(monkeypatch, tmp_path):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path))
    monkeypatch.setattr(run_service.cloud_storage, 'enabled', lambda: True)
    remote = {}
    monkeypatch.setattr(run_service.cloud_storage, 'save_run', lambda workspace, rid, data: remote.update({(workspace, rid): data}))
    monkeypatch.setattr(run_service.cloud_storage, 'load_run', lambda workspace, rid: remote.get((workspace, rid)))
    monkeypatch.setattr(run_service, '_capacity', threading.BoundedSemaphore(1))
    monkeypatch.setattr(run_service, '_active', set())
    monkeypatch.setattr(run_service, '_cloud_progress', {})
    return remote


def test_poll_from_a_fresh_instance_does_not_fail_active_import(hosted_runs):
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    run.status = RunStatus.RUNNING
    run_service._save(run, workspace)
    run_service._active.clear()
    run_service._path(run.id).unlink()
    assert run_service.get_run(run.id, workspace).status == RunStatus.RUNNING
    with pytest.raises(WorkspaceError) as error:
        run_service.get_run(run.id, 'c' * 64)
    assert error.value.status == 404


def test_storage_failure_does_not_leak_capacity(hosted_runs, monkeypatch):
    def unavailable(*args):
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Unavailable', 503)
    monkeypatch.setattr(run_service.cloud_storage, 'save_run', unavailable)
    for _ in range(3):
        with pytest.raises(WorkspaceError) as error:
            run_service.reserve_run('b' * 64)
        assert error.value.status == 503
        assert not run_service._active


def test_hosted_import_completes_within_request(hosted_runs, monkeypatch):
    calls = []
    monkeypatch.setattr(run_service, '_import', lambda *args: calls.append(args))
    run = run_service.reserve_run('b' * 64)
    run_service.submit_import(run, 'b' * 64, github_url='https://github.com/IBM/example')
    assert len(calls) == 1
    assert calls[0][4] == 'https://github.com/IBM/example'
