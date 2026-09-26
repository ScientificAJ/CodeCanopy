import pytest

from app.analyzers.python_analyzer import PythonAnalyzer
from app.services.analyzer_service import AnalyzerService, UnsupportedLanguageError


def test_python_analyzer_reports_symbols_and_imports_with_line_ranges() -> None:
    source = (
        "import os\n"
        "from database import connect\n"
        "\n"
        "def build():\n"
        "    pass\n"
        "\n"
        "async def load():\n"
        "    pass\n"
        "\n"
        "class Project:\n"
        "    def method(self):\n"
        "        return build()\n"
    )
    result = PythonAnalyzer().analyze(source, path="auth.py")

    assert result.path == "auth.py"
    assert result.name == "auth.py"
    assert result.language == "python"
    assert result.size == len(source.encode("utf-8"))
    assert [(symbol.name, symbol.line_start, symbol.line_end) for symbol in result.functions] == [
        ("build", 4, 5),
        ("load", 7, 8),
        ("method", 11, 12),
    ]
    assert [(symbol.name, symbol.line_start, symbol.line_end) for symbol in result.classes] == [("Project", 10, 12)]
    assert {symbol.file for symbol in result.functions + result.classes} == {"auth.py"}
    assert result.imports == ["os", "database"]


def test_analyzer_service_selects_by_file_extension() -> None:
    service = AnalyzerService(analyzers=(PythonAnalyzer(),))

    result = service.analyze("src/module.PY", "def run():\n    pass\n")

    assert result.path == "src/module.PY"
    assert [symbol.name for symbol in result.functions] == ["run"]


def test_analyzer_service_rejects_unsupported_extensions() -> None:
    service = AnalyzerService(analyzers=(PythonAnalyzer(),))

    with pytest.raises(UnsupportedLanguageError):
        service.analyze("src/module.ts", "export function run() {}")
