import ast
import copy
import hashlib
from pathlib import Path

from app.analyzers.base import SourceAnalyzer
from app.models.codebase import Class, File, Function


class _StructureNormalizer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = "identifier"
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = "parameter"
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        node.attr = "attribute"
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.name = "function"
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.name = "function"
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.name = "class"
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        node.value = type(node.value).__name__
        return node


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _structural_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized = _StructureNormalizer().visit(copy.deepcopy(node))
    shape = ast.dump(normalized, include_attributes=False)
    return hashlib.sha256(shape.encode("utf-8")).hexdigest()


def _structural_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    signature = []
    for child in ast.walk(node):
        signature.append(type(child).__name__)
        if isinstance(child, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop)):
            signature.append(type(child).__name__)
    return signature


class PythonAnalyzer(SourceAnalyzer):
    language = "python"
    file_extensions = (".py",)

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        module = ast.parse(source, filename=path)
        functions: list[Function] = []
        classes: list[Class] = []
        imports: list[str] = []
        references: set[str] = set()
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
                calls = sorted(
                    {
                        name
                        for child in ast.walk(node)
                        if isinstance(child, ast.Call)
                        if (name := _call_name(child.func)) is not None
                    }
                )
                functions.append(
                    Function(
                        name=node.name,
                        file=path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        calls=calls,
                        structural_hash=_structural_hash(node),
                        structural_signature=_structural_signature(node),
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

        for node in ast.walk(module):
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name:
                    references.add(name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                references.add(node.id)

        return File(
            path=path,
            name=Path(path).name,
            language=self.language,
            size=file_size,
            functions=functions,
            classes=classes,
            imports=imports,
            references=sorted(references),
        )
