from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.codebase import File as CodeFile, Project
from app.models.placeholder import PlaceholderResponse
from app.models.project import ProjectUploadResponse
from app.services.project_analysis import ProjectAnalysisError, analyze_project_files
from app.services.project_archive import ProjectUploadError, ProjectUploadTooLargeError
from app.services.project_storage import (
    ProjectNotFoundError,
    get_project,
    get_project_files,
    store_project_archive,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_project(file: UploadFile = File(...)) -> ProjectUploadResponse:
    try:
        return await store_project_archive(file)
    except ProjectUploadTooLargeError as error:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)) from error
    except ProjectUploadError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{project_id}", response_model=Project)
def read_project(project_id: str) -> Project:
    try:
        return get_project(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{project_id}/files", response_model=list[CodeFile])
def read_project_files(project_id: str) -> list[CodeFile]:
    try:
        return get_project_files(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{project_id}/analyze", response_model=list[CodeFile])
def analyze_project(project_id: str) -> list[CodeFile]:
    try:
        return analyze_project_files(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ProjectAnalysisError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
