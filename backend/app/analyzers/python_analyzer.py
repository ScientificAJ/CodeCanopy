import ast
from pathlib import Path

from app.analyzers.base import SourceAnalyzer
from app.models.codebase import Class, File, Function


class PythonAnalyzer(SourceAnalyzer):
    language = "python"
    file_extensions = (".py",)

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        module = ast.parse(source, filename=path)
        functions: list[Function] = []
        classes: list[Class] = []
        imports: list[str] = []
        file_size = size if size is not None else len(source.encode("utf-8"))

        relevant_nodes = (
            node
            for node in ast.walk(module)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom),
            )
        )
        nodes = sorted(relevant_nodes, key=lambda node: (node.lineno, node.col_offset))
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    Function(
                        name=node.name,
                        file=path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                classes.append(
                    Class(
                        name=node.name,
                        file=path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                    )
                )
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{'.' * node.level}{node.module or ''}")

        return File(
            path=path,
            name=Path(path).name,
            language=self.language,
            size=file_size,
            functions=functions,
            classes=classes,
            imports=imports,
        )
