import re
from pathlib import Path

from app.models.codebase import CallSite, File, Function

_FN_DEF = re.compile(
    r'(?:^|[\s;{(,])(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('
    r'|(?:^|[\s;{(,])(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|(\w+))\s*=>'
    r'|(?:^|[\s;{(,])(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(',
    re.MULTILINE,
)

_METHOD_DEF = re.compile(r'^\s*(?:async\s+)?(\w+)\s*\(', re.MULTILINE)

_CALL_SITE = re.compile(r'\b(\w+)\s*\(')

_IMPORT_FROM = re.compile(r'import\s+(?:[^"\']+\s+from\s+)?["\']([^"\']+)["\']')
_REQUIRE = re.compile(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)')

_KEYWORDS = frozenset({
    'if', 'for', 'while', 'switch', 'catch', 'function', 'return',
    'typeof', 'instanceof', 'new', 'delete', 'void', 'throw', 'case',
    'import', 'export', 'class', 'extends', 'super', 'yield', 'await',
    'async', 'let', 'const', 'var', 'of', 'in',
})


class JSAnalyzer:
    language = "javascript"
    file_extensions = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

    def analyze(self, source: str, path: str, size: int | None = None) -> File:
        functions: list[Function] = []
        call_sites: list[CallSite] = []
        imports: list[str] = []
        file_size = size if size is not None else len(source.encode("utf-8"))
        defined_names: set[str] = set()

        lines = source.splitlines()
        for lineno, line in enumerate(lines, start=1):
            # imports
            for m in _IMPORT_FROM.finditer(line):
                imports.append(m.group(1))
            for m in _REQUIRE.finditer(line):
                imports.append(m.group(1))

            # function definitions
            for m in _FN_DEF.finditer(line):
                name = next((g for g in m.groups() if g), None)
                if name and name not in _KEYWORDS:
                    functions.append(Function(name=name, file=path, line_start=lineno, line_end=lineno))
                    defined_names.add(name)

        # call sites — second pass after all definitions are known
        for lineno, line in enumerate(lines, start=1):
            # skip comment lines
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
