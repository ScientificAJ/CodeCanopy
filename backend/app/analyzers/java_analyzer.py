import re
from pathlib import Path

from app.models.codebase import CallSite, File, Function

# Method/function definition: visibility modifiers + return type + name + (
_METHOD_DEF = re.compile(
    r'(?:(?:public|private|protected|static|final|abstract|synchronized|native|strictfp)\s+)*'
    r'(?:<[^>]+>\s+)?'            # optional generic return type
    r'(\w+(?:\[\])*)\s+'          # return type (required for methods, not constructors)
    r'(\w+)\s*\(',
    re.MULTILINE,
)

_CALL_SITE = re.compile(r'\b(\w+)\s*\(')

_IMPORT = re.compile(r'^import\s+(?:static\s+)?([\w.]+)\s*;', re.MULTILINE)

_KEYWORDS = frozenset({
    'if', 'for', 'while', 'switch', 'catch', 'return', 'new', 'throw',
    'super', 'this', 'assert', 'synchronized', 'instanceof',
})

_PRIMITIVE_TYPES = frozenset({
    'void', 'int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short',
    'String', 'Object', 'List', 'Map', 'Set', 'Optional', 'Stream',
})


class JavaAnalyzer:
    language = "java"
    file_extensions = (".java",)

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        functions: list[Function] = []
        call_sites: list[CallSite] = []
        imports: list[str] = []
        file_size = size if size is not None else len(source.encode("utf-8"))

        lines = source.splitlines()

        # imports
        for m in _IMPORT.finditer(source):
            imports.append(m.group(1))

        # methods — skip constructors: return type starts with uppercase and not a known type
        for m in _METHOD_DEF.finditer(source):
            return_type = m.group(1)
            name = m.group(2)
            if name in _KEYWORDS:
                continue
            # constructors have no return type — heuristic: skip if return_type is uppercase
            # and not a primitive/known type (i.e. it looks like a class name)
            if return_type[0].isupper() and return_type not in _PRIMITIVE_TYPES:
                continue
            # find the line number
            lineno = source[: m.start()].count('\n') + 1
            functions.append(Function(name=name, file=path, line_start=lineno, line_end=lineno))

        # call sites
        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith('//') or stripped.startswith('*'):
                continue
            for m in _CALL_SITE.finditer(line):
                name = m.group(1)
                if name not in _KEYWORDS:
                    call_sites.append(CallSite(callee_name=name, file=path, line_start=lineno, line_end=lineno))

        return File(
            path=path,
            name=Path(path).name,
            language=self.language,
            size=file_size,
            functions=functions,
            call_sites=call_sites,
            imports=imports,
        )
