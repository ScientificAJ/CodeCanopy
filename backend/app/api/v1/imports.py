"""Both imports create durable runs and feed the same immutable snapshot store."""
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.api.v1.session import workspace_session
from app.models.v1.snapshot import AnalysisRun, ImportAccepted
from app.services.github_import import parse_github_url, GitHubImportError
from app.services.project_archive import _save_upload, ProjectUploadError, ProjectUploadTooLargeError
from app.services.run_service import reserve_run, submit_import, abandon_run, get_run, cancel_run
from app.services.v1_errors import WorkspaceError

router = APIRouter(tags=['v1-imports'])


class GitHubImportRequest(BaseModel):
    url: str = Field(max_length=500)
    ref: str = Field(default='HEAD', max_length=200)


@router.post('/imports/zip', response_model=ImportAccepted, status_code=202)
async def import_zip(file: UploadFile = File(...), workspace: str = Depends(workspace_session)):
    run = reserve_run(workspace)
    staging = Path(tempfile.mkdtemp(prefix='codecanopy-upload-'))
    archive = staging / 'upload.zip'
    try:
        await _save_upload(file, archive)
    except Exception as error:
        abandon_run(run, workspace)
        shutil.rmtree(staging, ignore_errors=True)
        if isinstance(error, ProjectUploadTooLargeError):
            raise WorkspaceError('UPLOAD_TOO_LARGE', str(error), 413) from None
        if isinstance(error, ProjectUploadError):
            raise WorkspaceError('INVALID_ARCHIVE', str(error), 400) from None
        raise
    finally:
        await file.close()
    name = (file.filename or 'Repository.zip').replace('\\', '/').rsplit('/', 1)[-1]
    if name.lower().endswith('.zip'):
        name = name[:-4]
    submit_import(run, workspace, archive=archive, name=' '.join(name.split())[:100] or 'Repository')
    return ImportAccepted(run_id=run.id, project_id=run.project_id)


@router.post('/imports/github', response_model=ImportAccepted, status_code=202)
def import_github(request: GitHubImportRequest, workspace: str = Depends(workspace_session)):
    try:
        parse_github_url(request.url)
    except GitHubImportError as error:
        raise WorkspaceError('INVALID_GITHUB_URL', str(error)) from None
    run = reserve_run(workspace)
    submit_import(run, workspace, github_url=request.url, ref=request.ref)
    return ImportAccepted(run_id=run.id, project_id=run.project_id)


@router.get('/runs/{run_id}', response_model=AnalysisRun)
def read_run(run_id: str, workspace: str = Depends(workspace_session)):
    return get_run(run_id, workspace)


@router.post('/runs/{run_id}/cancel', response_model=AnalysisRun, status_code=202)
def cancel_import(run_id: str, workspace: str = Depends(workspace_session)):
    return cancel_run(run_id, workspace)
