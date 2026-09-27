from pathlib import Path
from app.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
from app.models.codebase import File


class JSAnalyzer:
    language = "javascript"
    file_extensions = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        language = "typescript" if Path(path).suffix.lower() in {".ts", ".tsx"} else "javascript"
        return TreeSitterAnalyzer().analyze(source, path, language, size)
