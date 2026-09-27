from app.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
from app.models.codebase import File


class JavaAnalyzer:
    language = "java"
    file_extensions = (".java",)

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        return TreeSitterAnalyzer().analyze(source, path, self.language, size)
