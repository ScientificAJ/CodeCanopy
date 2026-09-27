import pytest

from app.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer, parser_language


@pytest.mark.parametrize(
    ('language', 'path', 'source', 'name', 'call'),
    [
        ('javascript', 'a.js', 'function validateEmail(value) { return check(value); }', 'validateEmail', 'check'),
        ('typescript', 'a.ts', 'export function validateEmail(value: string) { return check(value); }', 'validateEmail', 'check'),
        ('typescript', 'a.tsx', 'export function validateEmail(value: string) { return check(value); }', 'validateEmail', 'check'),
        ('go', 'a.go', 'func validateEmail(value string) bool { return check(value) }', 'validateEmail', 'check'),
        ('rust', 'a.rs', 'fn validate_email(value: i32) -> bool { check(value) }', 'validate_email', 'check'),
        ('java', 'A.java', 'class A { boolean validateEmail(String value) { return check(value); } }', 'validateEmail', 'check'),
        ('kotlin', 'A.kt', 'fun validateEmail(value: String): Boolean { return check(value) }', 'validateEmail', 'check'),
        ('c', 'a.c', 'int validate_email(int value) { return check(value); }', 'validate_email', 'check'),
        ('cpp', 'a.cpp', 'int validate_email(int value) { return check(value); }', 'validate_email', 'check'),
        ('csharp', 'A.cs', 'class A { bool ValidateEmail(string value) { return Check(value); } }', 'ValidateEmail', 'Check'),
        ('ruby', 'a.rb', 'def validate_email(value); check(value); end', 'validate_email', 'check'),
        ('php', 'a.php', '<?php function validate_email($value) { return check($value); }', 'validate_email', 'check'),
        ('shell', 'a.sh', 'validate_email() { check "$1"; }', 'validate_email', 'check'),
        ('sql', 'a.sql', 'CREATE FUNCTION validate_email(value INT) RETURNS INT AS $$ SELECT check(value); $$ LANGUAGE SQL;', 'validate_email', 'check'),
    ],
)
def test_extracts_function_references_for_supported_languages(language, path, source, name, call):
    result = TreeSitterAnalyzer().analyze(source, path, language)

    assert len(result.functions) == 1
    assert result.functions[0].name == name
    assert call is None or call in result.functions[0].calls
    assert result.functions[0].structural_hash


def test_selects_tsx_grammar_and_leaves_unsupported_swift_unparsed():
    assert parser_language('typescript', 'src/component.tsx') == 'tsx'
    assert parser_language('swift', 'src/component.swift') is None