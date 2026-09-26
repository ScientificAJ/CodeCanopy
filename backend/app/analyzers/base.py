from typing import Protocol

from app.models.codebase import File


class SourceAnalyzer(Protocol):
    language: str
    file_extensions: tuple[str, ...]

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        """Parse source text and return structured language-specific data."""
