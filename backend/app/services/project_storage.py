import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from pydantic import ValidationError

from app.models.codebase import File, Project
from app.models.project import ProjectUploadResponse
from app.services.project_archive import IGNORED_DIRECTORIES, extract_project_archive

PROJECT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class ProjectNotFoundError(LookupError):
    pass


def _projects_root() -> Path:
    configured_root = os.environ.get("GREPO_PROJECTS_DIR")
    root = Path(configured_root) if configured_root else Path(tempfile.gettempdir()) / "grepo" / "projects"
    return root.expanduser().resolve()


def get_project_directory(project_id: str) -> Path:
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ProjectNotFoundError("Project not found.")

    root = _projects_root()
    project_directory = root / project_id
    if project_directory.is_symlink() or not project_directory.is_dir():
        raise ProjectNotFoundError("Project not found.")
    return project_directory


def get_project(project_id: str) -> Project:
    project_directory = get_project_directory(project_id)
    metadata_path = _projects_root() / f"{project_id}.json"
    try:
        project_metadata = Project.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise ProjectNotFoundError("Project not found.") from error
    if project_metadata.id != project_id:
        raise ProjectNotFoundError("Project not found.")
    return Project(
        id=project_metadata.id,
        name=project_metadata.name,
        files=get_project_files_from_directory(project_directory),
    )


def _language_for_path(path: Path) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".json": "json",
        ".md": "markdown",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
    }.get(path.suffix.lower(), "unknown")


def get_project_files(project_id: str) -> list[File]:
    return get_project_files_from_directory(get_project_directory(project_id))


def get_project_files_from_directory(project_directory: Path) -> list[File]:
    files: list[File] = []
    for current_directory, directories, filenames in os.walk(project_directory, followlinks=False):
        current_path = Path(current_directory)
        directories[:] = sorted(
            directory
            for directory in directories
            if directory.casefold() not in IGNORED_DIRECTORIES
            and not (current_path / directory).is_symlink()
        )
        for filename in sorted(filenames):
            source_path = current_path / filename
            if source_path.is_symlink():
                continue
            try:
                relative_path = source_path.resolve().relative_to(project_directory.resolve()).as_posix()
                size = source_path.stat().st_size
            except (OSError, ValueError):
                continue
            files.append(
                File(
                    path=relative_path,
                    name=source_path.name,
                    language=_language_for_path(source_path),
                    size=size,
                )
            )
    return files


def _project_name(filename: str | None) -> str:
    archive_name = (filename or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    if archive_name.lower().endswith(".zip"):
        archive_name = archive_name[:-4]
    return archive_name.strip()[:100] or "Untitled project"


async def store_project_archive(upload: UploadFile) -> ProjectUploadResponse:
    root = _projects_root()
    root.mkdir(parents=True, exist_ok=True)
    project_id = uuid.uuid4().hex
    staging_directory = root / f".{project_id}.staging"
    extraction_root = staging_directory / "files"
    archive_path = staging_directory / "upload.zip"
    metadata_staging_path = staging_directory / "project.json"
    project_directory = root / project_id
    metadata_path = root / f"{project_id}.json"
    project_name = _project_name(upload.filename)
    staging_directory.mkdir()
    directory_published = False
    metadata_published = False
    complete = False

    try:
        file_count = await extract_project_archive(upload, archive_path, extraction_root)

        archive_path.unlink()
        metadata_staging_path.write_text(
            Project(id=project_id, name=project_name).model_dump_json(exclude={"files"}),
            encoding="utf-8",
        )
        extraction_root.replace(project_directory)
        directory_published = True
        metadata_staging_path.replace(metadata_path)
        metadata_published = True
        response = ProjectUploadResponse(project_id=project_id, name=project_name, file_count=file_count)
        complete = True
        return response
    finally:
        if not complete:
            if metadata_published:
                metadata_path.unlink(missing_ok=True)
            if directory_published:
                shutil.rmtree(project_directory, ignore_errors=True)
        if staging_directory.exists():
            shutil.rmtree(staging_directory, ignore_errors=True)