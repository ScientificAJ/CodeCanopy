from pathlib import Path

from app.analyzers.base import SourceAnalyzer
from app.models.codebase import File


class UnsupportedLanguageError(ValueError):
    pass


class AnalyzerService:
    def __init__(self, analyzers: tuple[SourceAnalyzer, ...]) -> None:
        self._analyzers = {
            extension.lower(): analyzer
            for analyzer in analyzers
            for extension in analyzer.file_extensions
        }

    def analyze(self, file_path: str | Path, source: str, size: int | None = None) -> File:
        extension = Path(file_path).suffix.lower()
        analyzer = self._analyzers.get(extension)
        if analyzer is None:
            raise UnsupportedLanguageError(f"No analyzer registered for '{extension or 'unknown'}'")
        return analyzer.analyze(source, path=Path(file_path).as_posix(), size=size)
