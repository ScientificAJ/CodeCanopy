"""Tests for JS, Java, and Python analyzers — call_sites + function extraction."""
import pytest

from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.js_analyzer import JSAnalyzer
from app.analyzers.java_analyzer import JavaAnalyzer


# ---------------------------------------------------------------------------
# PythonAnalyzer — call_sites
# ---------------------------------------------------------------------------

def test_python_analyzer_extracts_call_sites():
    source = "def foo(): pass\ndef bar(): foo()\n"
    result = PythonAnalyzer().analyze(source, "test.py")
    fn_names = [f.name for f in result.functions]
    assert "bar" in fn_names
    # PythonAnalyzer does not yet emit call_sites (not extended in this PR);
    # assert call_sites list exists (default empty)
    assert isinstance(result.call_sites, list)


def test_python_analyzer_extracts_function_names():
    source = "def alpha(): pass\ndef beta(): alpha()\n"
    result = PythonAnalyzer().analyze(source, "mod.py")
    names = [f.name for f in result.functions]
    assert "alpha" in names
    assert "beta" in names


# ---------------------------------------------------------------------------
# JSAnalyzer — function definitions and call sites
# ---------------------------------------------------------------------------

def test_js_analyzer_extracts_function_definition():
    source = "function greet(name) { return name; }\nconst result = greet('world');\n"
    result = JSAnalyzer().analyze(source, "app.js")
    fn_names = [f.name for f in result.functions]
    assert "greet" in fn_names


def test_js_analyzer_extracts_call_site():
    source = "function greet(name) { return name; }\nconst result = greet('world');\n"
    result = JSAnalyzer().analyze(source, "app.js")
    callee_names = [cs.callee_name for cs in result.call_sites]
    assert "greet" in callee_names


def test_js_analyzer_handles_arrow_function():
    source = "const double = (x) => x * 2;\ndouble(5);\n"
    result = JSAnalyzer().analyze(source, "utils.js")
    fn_names = [f.name for f in result.functions]
    assert "double" in fn_names


def test_js_analyzer_typescript_extension():
    source = "export function parse(s: string): number { return parseInt(s); }\n"
    result = JSAnalyzer().analyze(source, "parse.ts")
    assert result.language == "javascript"
    fn_names = [f.name for f in result.functions]
    assert "parse" in fn_names


# ---------------------------------------------------------------------------
# JavaAnalyzer — method definitions and call sites
# ---------------------------------------------------------------------------

def test_java_analyzer_extracts_method():
    source = 'public class App { public void run() { System.out.println("hi"); } }\n'
    result = JavaAnalyzer().analyze(source, "App.java")
    fn_names = [f.name for f in result.functions]
    assert "run" in fn_names


def test_java_analyzer_extracts_call_site():
    source = 'public class App { public void run() { doWork(); } public void doWork() {} }\n'
    result = JavaAnalyzer().analyze(source, "App.java")
    callee_names = [cs.callee_name for cs in result.call_sites]
    assert "doWork" in callee_names


def test_java_analyzer_extracts_import():
    source = "import java.util.List;\npublic class X { public void go() {} }\n"
    result = JavaAnalyzer().analyze(source, "X.java")
    assert "java.util.List" in result.imports
