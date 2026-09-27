"""Single-process, bounded import workers with durable status and cancellation."""
from __future__ import annotations

import hashlib
import shutil
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.models.v1.snapshot import AnalysisRun, RunDiagnostic, RunStage, RunStatus
from app.services.project_archive import ProjectUploadError, _validated_entries, _extract_entries
from app.services.snapshot_service import (
    _v1_root, _read_json, _write_json, checked_id, create_snapshot_from_project,
    create_snapshot_from_github, delete_project,
)
from app.services.v1_errors import WorkspaceError

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='codecanopy-import')
_capacity = threading.BoundedSemaphore(4)
_lock = threading.RLock()
_active: set[str] = set()
TERMINAL = {RunStatus.COMPLETED, RunStatus.PARTIAL, RunStatus.FAILED, RunStatus.CANCELLED}


def _path(run_id: str) -> Path:
    return _v1_root() / f'run_{checked_id(run_id)}.json'


def _save(run: AnalysisRun, workspace: str):
    _write_json(_path(run.id), {**run.model_dump(mode='json'), 'workspace_id': workspace})


def get_run(run_id: str, workspace: str) -> AnalysisRun:
    with _lock:
        try:
            data = _read_json(_path(run_id))
        except (OSError, ValueError):
            raise WorkspaceError('NOT_FOUND', 'Import run not found.', 404) from None
        if data.get('workspace_id') != workspace:
            raise WorkspaceError('NOT_FOUND', 'Import run not found.', 404)
        run = AnalysisRun.model_validate(data)
        if run.status not in TERMINAL and run_id not in _active:
            run.status = RunStatus.FAILED
            run.event_sequence += 1
            run.diagnostics.append(RunDiagnostic(stage='import', message='Import interrupted by server restart. Please import again.', severity='error'))
            run.completed_at = datetime.now(timezone.utc)
            _save(run, workspace)
        return run


def reserve_run(workspace: str) -> AnalysisRun:
    if not _capacity.acquire(blocking=False):
        raise WorkspaceError('IMPORT_BUSY', 'Import capacity is full. Wait for an active import to finish.', 429)
    with _lock:
        run = AnalysisRun(id=uuid.uuid4().hex, project_id=uuid.uuid4().hex, status=RunStatus.QUEUED,
                          stage=RunStage.VALIDATE, started_at=datetime.now(timezone.utc))
        _active.add(run.id)
        _save(run, workspace)
        return run


def cancel_run(run_id: str, workspace: str) -> AnalysisRun:
    with _lock:
        run = get_run(run_id, workspace)
        if run.status not in TERMINAL:
            run.cancel_requested = True
            run.status = RunStatus.CANCELLED
            run.event_sequence += 1
            run.completed_at = datetime.now(timezone.utc)
            _save(run, workspace)
        return run


def abandon_run(run: AnalysisRun, workspace: str):
    with _lock:
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        _save(run, workspace)
        _active.discard(run.id)
        _capacity.release()


def submit_import(run: AnalysisRun, workspace: str, *, archive: Path | None = None,
                  name: str = 'Repository', github_url: str | None = None, ref: str = 'HEAD'):
    _executor.submit(_import, run, workspace, archive, name, github_url, ref)


def _import(run, workspace, archive, name, github_url, ref):
    staging = archive.parent if archive else None
    snapshot = None
    skipped_links = []
    deadline = time.monotonic() + 180

    def check_cancel():
        if get_run(run.id, workspace).cancel_requested:
            raise WorkspaceError('CANCELLED', 'Import cancelled.', 409)
        if time.monotonic() > deadline:
            raise WorkspaceError('IMPORT_TIMEOUT', 'Import exceeded its three-minute processing limit.', 408)

    def stage(value):
        with _lock:
            check_cancel()
            run.stage = value
            run.stage_progress = None
            run.status = RunStatus.RUNNING
            run.event_sequence += 1
            _save(run, workspace)

    last_progress = 0.0

    def report_progress(done, total):
        nonlocal last_progress
        now = time.monotonic()
        if done not in (0, total) and now - last_progress < 0.4:
            return
        with _lock:
            check_cancel()
            run.stage_progress = done / total if total else 1
            run.event_sequence += 1
            _save(run, workspace)
        last_progress = now

    try:
        stage(RunStage.SNAPSHOT)
        if github_url:
            from app.services.github_import import import_github_repository
            owner, repo, commit, display_ref, name, files, staging = import_github_repository(github_url, ref, check_cancel, skipped_links.append)
            stage(RunStage.INVENTORY)
            _, snapshot, _ = create_snapshot_from_github(owner, repo, commit, display_ref, name, files,
                project_id=run.project_id, workspace_id=workspace, run_id=run.id, check_cancel=check_cancel, report_progress=report_progress)
        else:
            files = staging / 'files'
            with archive.open('rb') as uploaded:
                digest = hashlib.file_digest(uploaded, 'sha256').hexdigest()
            with zipfile.ZipFile(archive) as zf:
                _extract_entries(zf, _validated_entries(zf, check_cancel, skip_symlinks=True, on_skip=skipped_links.append), files, check_cancel)
            stage(RunStage.INVENTORY)
            snapshot, _ = create_snapshot_from_project(run.project_id, files, digest, name,
                workspace_id=workspace, run_id=run.id, check_cancel=check_cancel, report_progress=report_progress)
        # Publish the terminal run under the cancellation lock. If cancellation won
        # the race, remove the just-created project instead of exposing a late result.
        with _lock:
            check_cancel()
            run.snapshot_id = snapshot.id
            run.result_snapshot_id = snapshot.id
            run.diagnostics = [RunDiagnostic.model_validate(d) for d in _read_json(_v1_root() / snapshot.id / 'diagnostics.json')]
            if skipped_links:
                run.diagnostics.append(RunDiagnostic(stage='import', message=f'{len(skipped_links)} symbolic link(s) skipped; link targets were not followed.'))
            run.status = RunStatus.PARTIAL if run.diagnostics else RunStatus.COMPLETED
            run.stage = RunStage.INVENTORY
            run.stage_progress = 1
            run.event_sequence += 1
            run.completed_at = datetime.now(timezone.utc)
            _save(run, workspace)
    except Exception as error:
        if snapshot:
            delete_project(run.project_id, workspace)
        with _lock:
            current = get_run(run.id, workspace)
            if current.status != RunStatus.CANCELLED:
                from app.services.github_import import GitHubImportError
                message = str(error) if isinstance(error, (WorkspaceError, ProjectUploadError, GitHubImportError)) else 'Import failed. Check that this is a valid supported repository archive.'
                current.status = RunStatus.FAILED
                current.diagnostics.append(RunDiagnostic(stage='import', message=message, severity='error'))
                current.event_sequence += 1
                current.completed_at = datetime.now(timezone.utc)
                _save(current, workspace)
    finally:
        if staging:
            shutil.rmtree(staging, ignore_errors=True)
        with _lock:
            _active.discard(run.id)
        _capacity.release()
