import os
import tokenize
from pathlib import Path

from app.core.analyzers import analyzer_service
from app.models.codebase import File
from app.services.project_archive import IGNORED_DIRECTORIES
from app.services.project_storage import (
    ProjectNotFoundError,
    get_project_directory,
)


class ProjectAnalysisError(ValueError):
    pass


def analyze_project_files(project_id: str) -> list[File]:
    project_directory = get_project_directory(project_id)
    resolved_project_directory = project_directory.resolve()
    results: list[File] = []

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
            if source_path.is_symlink() or source_path.suffix.lower() != ".py":
                continue

            resolved_source_path = source_path.resolve()
            try:
                relative_path = resolved_source_path.relative_to(resolved_project_directory)
            except ValueError:
                continue

            relative_path_text = relative_path.as_posix()
            try:
                with tokenize.open(source_path) as source_file:
                    source = source_file.read()
            except (SyntaxError, UnicodeDecodeError, LookupError) as error:
                raise ProjectAnalysisError(f"Could not read Python source at '{relative_path_text}'.") from error

            try:
                results.append(
                    analyzer_service.analyze(
                        relative_path_text,
                        source,
                        size=source_path.stat().st_size,
                    )
                )
            except SyntaxError as error:
                raise ProjectAnalysisError(f"Could not parse Python source at '{relative_path_text}'.") from error

    return results