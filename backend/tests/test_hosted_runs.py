"""Hosted work cannot depend on a warm process or detached worker lifetime."""
import threading

import pytest

from app.models.v1.snapshot import RunStatus
from app.services import run_service
from app.services.v1_errors import WorkspaceError


@pytest.fixture
def hosted_runs(monkeypatch, tmp_path):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path))
    monkeypatch.setattr(run_service.cloud_storage, 'enabled', lambda: True)
    remote = {}
    cancelled = set()
    monkeypatch.setattr(run_service.cloud_storage, 'request_cancel', lambda workspace, rid: cancelled.add((workspace, rid)), raising=False)
    monkeypatch.setattr(run_service.cloud_storage, 'cancellation_requested', lambda workspace, rid: (workspace, rid) in cancelled, raising=False)
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


def test_remote_cancellation_wins_over_a_stale_progress_write(hosted_runs):
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    # A different instance accepts cancellation. The worker still holds its
    # original queued object, then attempts to publish fresh progress.
    run_service.cloud_storage.request_cancel(workspace, run.id)
    run.status = RunStatus.RUNNING
    run_service._save(run, workspace)
    assert run.cancel_requested
    assert hosted_runs[(workspace, run.id)]['status'] == RunStatus.CANCELLED
    assert run_service.get_run(run.id, workspace).status == RunStatus.CANCELLED


def test_remote_cancellation_is_observed_by_active_worker(hosted_runs, monkeypatch, tmp_path):
    from app.services import github_import
    workspace = 'b' * 64
    clock = [100.0]
    monkeypatch.setattr(run_service.time, 'monotonic', lambda: clock[0])
    run = run_service.reserve_run(workspace)

    def download(url, ref, check_cancel, on_skip):
        check_cancel()
        run_service.cloud_storage.request_cancel(workspace, run.id)
        clock[0] += 3
        check_cancel()
        raise AssertionError('Cancelled import must not continue downloading')

    monkeypatch.setattr(github_import, 'import_github_repository', download)
    run_service.submit_import(run, workspace, github_url='https://github.com/IBM/example')
    assert hosted_runs[(workspace, run.id)]['status'] == RunStatus.CANCELLED
    assert not run_service._active
    assert run_service._capacity.acquire(blocking=False)


def test_cancellation_during_publication_removes_late_project(hosted_runs, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from app.services import github_import
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    staging = tmp_path / 'download'
    staging.mkdir()
    monkeypatch.setattr(github_import, 'import_github_repository', lambda *args: ('IBM', 'example', 'rev', 'main', 'Example', staging, staging))
    removed = []
    monkeypatch.setattr(run_service, 'delete_project', lambda pid, wid: removed.append((pid, wid)))

    def publish(*args, **kwargs):
        # Another instance accepts a cancellation while a source bundle is
        # being uploaded. The worker must revoke this late project afterward.
        run_service.cloud_storage.request_cancel(workspace, run.id)
        return run.project_id, SimpleNamespace(id='a' * 32), []

    monkeypatch.setattr(run_service, 'create_snapshot_from_github', publish)
    run_service.submit_import(run, workspace, github_url='https://github.com/IBM/example')
    assert removed == [(run.project_id, workspace)]
    saved = hosted_runs[(workspace, run.id)]
    assert saved['status'] == RunStatus.CANCELLED
    assert saved['snapshot_id'] is None and saved['result_snapshot_id'] is None


def test_cancellation_marker_masks_a_stale_remote_completion(hosted_runs):
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    stale = dict(hosted_runs[(workspace, run.id)])
    stale['status'] = RunStatus.COMPLETED
    stale['snapshot_id'] = 'a' * 32
    stale['result_snapshot_id'] = 'a' * 32
    hosted_runs[(workspace, run.id)] = stale
    run_service.cloud_storage.request_cancel(workspace, run.id)
    run_service._active.clear()
    response = run_service.get_run(run.id, workspace)
    assert response.status == RunStatus.CANCELLED
    assert response.snapshot_id is None and response.result_snapshot_id is None


def test_inactive_hosted_run_expires_after_execution_window(hosted_runs):
    from datetime import datetime, timedelta, timezone
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc) - timedelta(minutes=7)
    run_service._save(run, workspace)
    run_service._active.clear()
    response = run_service.get_run(run.id, workspace)
    assert response.status == RunStatus.FAILED
    assert response.completed_at is not None
    assert 'hosted execution window' in response.diagnostics[-1].message
    assert hosted_runs[(workspace, run.id)]['status'] == RunStatus.FAILED


def test_recent_hosted_run_is_not_misclassified_as_interrupted(hosted_runs):
    from datetime import datetime, timedelta, timezone
    workspace = 'b' * 64
    run = run_service.reserve_run(workspace)
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    run_service._save(run, workspace)
    run_service._active.clear()
    assert run_service.get_run(run.id, workspace).status == RunStatus.RUNNING


def test_remote_archive_uses_seekable_stream_without_claiming_full_archive_digest(hosted_runs, monkeypatch, tmp_path):
    import io
    import zipfile
    from types import SimpleNamespace
    workspace = 'b' * 64
    contents = io.BytesIO()
    with zipfile.ZipFile(contents, 'w') as archive:
        archive.writestr('README.md', 'Retained source')
    staging = tmp_path / 'uploaded'
    staging.mkdir()

    class MemoryArchive(run_service.cloud_storage.RemoteBlobArchive):
        def open(self, mode='rb'):
            assert mode == 'rb'
            return io.BytesIO(contents.getvalue())

    remote_archive = MemoryArchive(f'uploads/{workspace}/' + 'a' * 32 + '.zip', workspace, staging)
    captured = []

    def create(project_id, files, digest, name, **kwargs):
        assert (files / 'README.md').read_text() == 'Retained source'
        captured.append(digest)
        sid = 'c' * 32
        (run_service._v1_root() / sid).mkdir()
        run_service._write_json(run_service._v1_root() / sid / 'diagnostics.json', [])
        return SimpleNamespace(id=sid), []

    monkeypatch.setattr(run_service, 'create_snapshot_from_project', create)
    run = run_service.reserve_run(workspace)
    run_service.submit_import(run, workspace, archive=remote_archive)
    assert captured == [None]
    assert hosted_runs[(workspace, run.id)]['status'] == RunStatus.COMPLETED
    assert not staging.exists()
