"""Bounded, non-executing syntax extraction for common repository languages."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import warnings

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

from app.models.codebase import CallSite, File, Function

FUNCTION_NODE_TYPES = {
    'javascript': {'function_declaration', 'function_expression', 'arrow_function', 'method_definition'},
    'typescript': {'function_declaration', 'function_expression', 'arrow_function', 'method_definition'},
    'tsx': {'function_declaration', 'function_expression', 'arrow_function', 'method_definition'},
    'go': {'function_declaration', 'method_declaration'},
    'rust': {'function_item'},
    'java': {'method_declaration', 'constructor_declaration'},
    'kotlin': {'function_declaration'},
    'c': {'function_definition'},
    'cpp': {'function_definition'},
    'csharp': {'method_declaration', 'local_function_statement', 'constructor_declaration', 'operator_declaration'},
    'ruby': {'method', 'singleton_method'},
    'php': {'function_definition', 'method_declaration'},
    'bash': {'function_definition'},
    'sql': {'create_function', 'create_function_statement', 'function_definition'},
}
ALL_FUNCTION_NODE_TYPES = frozenset(item for values in FUNCTION_NODE_TYPES.values() for item in values)
CALL_NODE_TYPES = {
    'call_expression', 'method_invocation', 'function_call_expression',
    'member_call_expression', 'scoped_call_expression', 'invocation_expression',
    'function_call', 'call', 'command',
    # tree-sitter-language-pack spells the SQL call node `invocation`; the
    # bundled `invocation_expression` above is the tree-sitter-languages name.
    'invocation',
}
IDENTIFIER_TYPES = {
    'identifier', 'type_identifier', 'field_identifier', 'property_identifier',
    'simple_identifier', 'name', 'word', 'command_name',
}
PARAMETER_CONTAINERS = {'formal_parameters', 'parameters', 'parameter_list', 'function_value_parameters', 'method_parameters'}
PARAMETER_DECLARATIONS = {
    'formal_parameter', 'required_parameter', 'parameter_declaration', 'parameter',
    'simple_parameter', 'value_parameter', 'optional_parameter', 'rest_parameter',
}
STRING_TYPES = {
    'string', 'string_literal', 'interpreted_string_literal', 'raw_string_literal',
    'template_string', 'char_literal', 'rune_literal', 'encapsed_string',
}
NUMBER_TYPES = {'number', 'number_literal', 'integer_literal', 'float_literal', 'decimal_integer_literal'}
BLOCK_TYPES = {'block', 'statement_block', 'compound_statement', 'function_body', 'body_statement'}
COMMENT_TYPES = {'comment', 'line_comment', 'block_comment', 'documentation_comment'}


def parser_language(language: str, path: str) -> str | None:
    if language == 'python':
        return None
    if language == 'typescript' and Path(path).suffix.lower() == '.tsx':
        return 'tsx'
    if language == 'csharp':
        return 'csharp'
    if language == 'shell':
        return 'bash'
    return language if language in FUNCTION_NODE_TYPES else None


def _walk(node: Node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _source_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')


def _identifier_node(node: Node, source: bytes) -> Node | None:
    nodes = list(_walk(node))
    return next((item for item in reversed(nodes) if item.type in IDENTIFIER_TYPES), None)


def _first_identifier_node(node: Node) -> Node | None:
    return next((item for item in _walk(node) if item.type in IDENTIFIER_TYPES), None)


def _parameter_name_node(node: Node, source: bytes) -> Node | None:
    for field in ('name', 'pattern', 'declarator', 'left'):
        candidate = node.child_by_field_name(field)
        if candidate is not None:
            identifier = _identifier_node(candidate, source)
            if identifier is not None:
                return identifier
    return _first_identifier_node(node)


def _declared_name_node(node: Node, source: bytes, language: str) -> Node | None:
    for field in ('name', 'method', 'function'):
        candidate = node.child_by_field_name(field)
        if candidate is not None:
            identifier = _identifier_node(candidate, source)
            if identifier is not None:
                return identifier

    if language in {'c', 'cpp'}:
        declarator = node.child_by_field_name('declarator')
        if declarator is not None:
            for candidate in _walk(declarator):
                if candidate.type == 'function_declarator':
                    target = candidate.child_by_field_name('declarator') or candidate
                    identifier = _identifier_node(target, source)
                    if identifier is not None:
                        return identifier

    if language == 'kotlin' and node.type == 'function_declaration':
        return _first_identifier_node(node)
    if language == 'sql' and node.type in {'create_function', 'create_function_statement'}:
        return _first_identifier_node(node)

    parent = node.parent
    for _ in range(3):
        if parent is None:
            break
        if parent.type in {'variable_declarator', 'field_definition', 'property_declaration', 'assignment'}:
            name = parent.child_by_field_name('name')
            if name is not None:
                identifier = _identifier_node(name, source)
                if identifier is not None:
                    return identifier
        parent = parent.parent
    return None


def _call_name(node: Node, source: bytes) -> str | None:
    for field in ('function', 'method', 'name', 'callee'):
        target = node.child_by_field_name(field)
        if target is not None:
            identifier = _identifier_node(target, source)
            if identifier is not None:
                return _source_text(identifier, source).strip('`"\'')
    last_target_types = {'member_expression', 'field_expression', 'scoped_identifier', 'qualified_identifier', 'attribute'}
    identifier = _identifier_node(node, source) if node.type in last_target_types else _first_identifier_node(node)
    return _source_text(identifier, source).strip('`"\'') if identifier else None


def _embedded_sql_roots(node: Node, source: bytes, parser) -> list[tuple[Node, bytes]]:
    """Extract the body of a dollar-quoted SQL function body.

    tree-sitter-languages 1.x parses `AS $$ ... $$` as a single `string` node.
    tree-sitter-language-pack instead emits `dollar_quote` delimiters with the
    body's own node (a `statement`) between them, so the body has to be located
    structurally instead of by quoting a single node's text.
    """
    roots = []
    body = node
    for child in _walk(node):
        if child.type == 'string' and any(parent.type == 'function_body' for parent in _ancestors(child)):
            body = child
            break
    else:
        for parent in _walk(node):
            if parent.type != 'function_body':
                continue
            children = parent.named_children
            for index, child in enumerate(children):
                if child.type != 'dollar_quote':
                    continue
                between = children[index + 1:-1] if index + 1 < len(children) - 1 else []
                statement = next((item for item in between if item.type not in {'dollar_quote'}), None)
                if statement is not None:
                    roots.append((statement, source[statement.start_byte:statement.end_byte]))
            break
    if roots:
        return roots
    raw = _source_text(body, source)
    match = re.match(r'^(\$[A-Za-z_0-9]*\$)(.*?)\1$', raw, re.DOTALL)
    if not match or not match.group(2).strip():
        return []
    embedded_source = match.group(2).encode('utf-8')
    embedded = parser.parse(embedded_source).root_node
    if not embedded.has_error:
        roots.append((embedded, embedded_source))
    return roots


def _ancestors(node: Node):
    parent = node.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def _shape_token(node: Node) -> str | None:
    if node.type in COMMENT_TYPES:
        return None
    if node.type in IDENTIFIER_TYPES:
        return 'identifier'
    if node.type in STRING_TYPES or 'string' in node.type:
        return 'string_literal'
    if node.type in NUMBER_TYPES or 'integer_literal' in node.type or 'float_literal' in node.type:
        return 'number_literal'
    if node.type in CALL_NODE_TYPES:
        return 'call_expression'
    if node.type in BLOCK_TYPES:
        return 'block'
    if node.type in ALL_FUNCTION_NODE_TYPES:
        return 'function_definition'
    return node.type


class TreeSitterAnalyzer:
    def analyze(self, source_text: str, path: str, language: str, size: int | None = None) -> File:
        parser_name = parser_language(language, path)
        if parser_name is None:
            raise ValueError(f"No syntax parser is configured for '{language}'.")
        source = source_text.encode('utf-8')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', FutureWarning)
            parser = get_parser(parser_name)
        tree = parser.parse(source)
        root = tree.root_node
        if root.has_error:
            raise SyntaxError(f"Could not parse {language} source.")

        definition_nodes = [node for node in _walk(root) if node.type in FUNCTION_NODE_TYPES[parser_name]]
        function_names = {
            (name.start_byte, name.end_byte)
            for node in definition_nodes
            if (name := _declared_name_node(node, source, parser_name)) is not None
        }
        parameter_names = set()
        for node in _walk(root):
            if node.type in PARAMETER_CONTAINERS:
                for child in node.named_children:
                    if child.type in IDENTIFIER_TYPES:
                        parameter_names.add((child.start_byte, child.end_byte))
                    elif child.type in PARAMETER_DECLARATIONS:
                        name = _parameter_name_node(child, source)
                        if name is not None:
                            parameter_names.add((name.start_byte, name.end_byte))
                    elif child.type == 'assignment_pattern':
                        left = child.child_by_field_name('left')
                        name = _identifier_node(left, source) if left is not None else None
                        if name is not None:
                            parameter_names.add((name.start_byte, name.end_byte))
            elif node.type in PARAMETER_DECLARATIONS:
                name = _parameter_name_node(node, source)
                if name is not None:
                    parameter_names.add((name.start_byte, name.end_byte))
        functions = []
        for node in definition_nodes:
            name_node = _declared_name_node(node, source, parser_name)
            if name_node is None:
                continue
            signature = [token for child in _walk(node) if (token := _shape_token(child)) is not None]
            embedded_roots = _embedded_sql_roots(node, source, parser) if parser_name == 'sql' else []
            for embedded, _ in embedded_roots:
                signature.append('embedded_sql')
                signature.extend(token for child in _walk(embedded) if (token := _shape_token(child)) is not None)
            calls = sorted({
                name
                for child in _walk(node)
                if child.type in CALL_NODE_TYPES
                if (name := _call_name(child, source)) is not None
            } | {
                name
                for embedded, embedded_source in embedded_roots
                for child in _walk(embedded)
                if child.type in CALL_NODE_TYPES
                if (name := _call_name(child, embedded_source)) is not None
            })
            structural_hash = hashlib.sha256(json.dumps(signature, separators=(',', ':')).encode()).hexdigest()
            functions.append(Function(
                name=_source_text(name_node, source).strip('`"\'/$'),
                file=path,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                calls=calls,
                structural_hash=structural_hash,
                structural_signature=signature,
            ))

        references = set()
        for node in _walk(root):
            if (node.type not in IDENTIFIER_TYPES
                    or (node.start_byte, node.end_byte) in function_names
                    or (node.start_byte, node.end_byte) in parameter_names):
                continue
            reference = _source_text(node, source).strip('`"\'/$')
            if reference:
                references.add(reference)

        imports = []
        for node in _walk(root):
            if parser_name == 'java' and node.type == 'import_declaration':
                imports.append(re.sub(r'^import\s+(?:static\s+)?|;\s*$', '', _source_text(node, source)).strip())
            elif parser_name in {'javascript', 'typescript', 'tsx'} and node.type == 'import_statement':
                module = node.child_by_field_name('source')
                if module is not None:
                    imports.append(_source_text(module, source).strip('\"\''))
        return File(
            path=path,
            name=Path(path).name,
            language=language,
            size=size if size is not None else len(source),
            imports=imports,
            functions=sorted(functions, key=lambda item: (item.line_start, item.name.casefold())),
            call_sites=[
                CallSite(callee_name=name, file=path,
                         line_start=node.start_point[0] + 1, line_end=node.end_point[0] + 1)
                for node in _walk(root) if node.type in CALL_NODE_TYPES
                if (name := _call_name(node, source)) is not None
            ],
            references=sorted(references),
        )
