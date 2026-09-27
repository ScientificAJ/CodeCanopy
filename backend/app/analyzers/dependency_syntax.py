"""Conservative static bindings; runs only inside the resource-limited parser worker.

Only module-level function bindings and explicit imports are resolved. No repository
code is imported or executed. Unsupported/ambiguous calls remain visible as unresolved.
"""
import ast
from collections import Counter
import warnings


def extract_dependencies(text, path, language):
    if language == 'python':
        return _python(text)
    if language in {'javascript', 'typescript'}:
        return _javascript(text, path, language)
    return None


def _python(text):
    root = ast.parse(text)
    definitions, imports, calls = [], [], []
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    bindings = Counter()
    for node in root.body:
        if isinstance(node, functions):
            definitions.append({'name': node.name, 'line': node.lineno, 'exports': [node.name]})
            bindings[node.name] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                local = alias.asname or (alias.name.split('.')[0] if isinstance(node, ast.Import) else alias.name)
                imports.append({'module': alias.name if isinstance(node, ast.Import) else '.' * node.level + (node.module or ''),
                                'symbol': None if isinstance(node, ast.Import) else alias.name,
                                'local': local, 'line': node.lineno,
                                'namespace': isinstance(node, ast.Import),
                                'prefix': alias.name if isinstance(node, ast.Import) and not alias.asname else local})
                bindings[local] += 1
    # Assignments anywhere at module scope, including conditional assignments, make
    # that name unsafe. Nested function locals are checked separately below.
    def assigned(nodes):
        found = set()
        for node in nodes:
            if isinstance(node, functions + (ast.ClassDef, ast.Lambda)):
                found.add(getattr(node, 'name', ''))
                continue
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                found.add(node.id)
            if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name:
                found.add(node.name)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                found.update(a.asname or a.name.split('.')[0] for a in node.names)
            found.update(assigned(ast.iter_child_nodes(node)))
        return found
    unsafe = assigned(n for n in root.body if not isinstance(n, functions + (ast.Import, ast.ImportFrom)))
    unsafe.update(n.name for n in root.body if isinstance(n, functions) and n.decorator_list)
    if any(i['symbol'] == '*' for i in imports):
        unsafe.update(bindings)
    def visit(node, caller=None, blocked=frozenset(), nested=False):
        if isinstance(node, functions):
            for default in [*node.args.defaults, *node.args.kw_defaults, *node.decorator_list]:
                if default is not None:
                    visit(default, caller, blocked, nested)
            params = {a.arg for a in ast.walk(node.args) if isinstance(a, ast.arg)}
            local = assigned(node.body) | params
            # Nested closures and class methods require scope/type inference.
            for child in node.body:
                visit(child, node.lineno, blocked | local, nested or caller is not None)
            return
        if isinstance(node, (ast.ClassDef, ast.Lambda)):
            for child in ast.iter_child_nodes(node):
                visit(child, caller, blocked, True)
            return
        if isinstance(node, ast.Call):
            parts, callee = [], node.func
            while isinstance(callee, ast.Attribute):
                parts.insert(0, callee.attr); callee = callee.value
            if isinstance(callee, ast.Name):
                parts.insert(0, callee.id)
            else:
                parts = []
            name = '.'.join(parts) or '<dynamic call>'
            eligible = bool(parts) and not nested and parts[0] not in blocked | unsafe and bindings[parts[0]] == 1
            calls.append({'name': name, 'line': node.lineno, 'end': node.end_lineno, 'caller': caller, 'eligible': eligible})
        for child in ast.iter_child_nodes(node):
            visit(child, caller, blocked, nested)
    visit(root)
    definitions = [d for d in definitions if d['name'] not in unsafe and bindings[d['name']] == 1]
    return {'version': 1, 'definitions': definitions, 'imports': imports, 'calls': calls}


def _javascript(text, path, language):
    from tree_sitter_languages import get_parser
    from app.analyzers.tree_sitter_analyzer import _walk, _ancestors, _declared_name_node, FUNCTION_NODE_TYPES
    parser_language = 'tsx' if path.endswith('.tsx') else language
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        root = get_parser(parser_language).parse(text.encode()).root_node
    source = text.encode()
    def value(node):
        return source[node.start_byte:node.end_byte].decode() if node is not None else ''
    types = FUNCTION_NODE_TYPES[parser_language]
    definitions, imports, calls = [], [], []
    bindings = Counter()
    top_functions = {}
    for node in _walk(root):
        if node.type in types:
            name_node = _declared_name_node(node, source, parser_language)
            ancestors = list(_ancestors(node))
            parent = node.parent
            # Only declarations or a direct variable initializer introduce a
            # module binding. A callback nested in an initializer does not.
            if node.type == 'function_declaration':
                owner = parent
            elif parent is not None and parent.type == 'variable_declarator' and parent.child_by_field_name('value') == node:
                owner = parent.parent.parent if parent.parent is not None else None
                # The legacy inventory names named function expressions by their
                # internal name, which is not a module binding. Leave unresolved.
                if node.child_by_field_name('name') is not None:
                    owner = None
            else:
                owner = None
            if owner is not None and owner.type == 'export_statement':
                owner = owner.parent
            top = owner is not None and owner.type == 'program'
            if name_node is not None and top:
                name = value(name_node)
                export = next((a for a in ancestors if a.type == 'export_statement'), None)
                exports = (['default'] if export and any(c.type == 'default' for c in export.children) else [name]) if export else []
                definitions.append({'name': name, 'line': node.start_point[0] + 1, 'exports': exports})
                bindings[name] += 1
                top_functions[node.start_byte] = name
        if node.type == 'import_statement':
            module = value(node.child_by_field_name('source')).strip('\"\'')
            clause = next((n for n in node.named_children if n.type == 'import_clause'), None)
            entries = []
            if clause:
                for child in clause.named_children:
                    if child.type == 'identifier': entries.append((value(child), 'default', False))
                    elif child.type == 'namespace_import': entries.append((value(child.named_children[-1]), None, True))
                    elif child.type == 'named_imports':
                        for spec in child.named_children:
                            name = spec.child_by_field_name('name')
                            alias = spec.child_by_field_name('alias')
                            if name: entries.append((value(alias or name), value(name), False))
            if not entries: entries = [('', None, False)]
            for local, symbol, namespace in entries:
                imports.append({'module': module, 'symbol': symbol, 'local': local, 'namespace': namespace, 'prefix': local, 'line': node.start_point[0] + 1})
                bindings[local] += 1
    # Conservatively reject shadowing anywhere in a file. This may omit valid calls,
    # but never turns a parameter/object method into an imported function target.
    shadowed = set()
    for node in _walk(root):
        if node.type == 'class_declaration':
            name = node.child_by_field_name('name')
            if name: shadowed.add(value(name))
        if node.type in {'formal_parameters', 'required_parameter', 'optional_parameter', 'assignment_expression', 'update_expression', 'catch_clause'}:
            shadowed.update(value(n) for n in _walk(node) if n.type == 'identifier')
        if node.type == 'variable_declarator':
            name, rhs = node.child_by_field_name('name'), node.child_by_field_name('value')
            if name is not None and (rhs is None or rhs.start_byte not in top_functions):
                shadowed.update(value(n) for n in _walk(name) if n.type == 'identifier')
        if node.type in types:
            param = node.child_by_field_name('parameter')
            if param: shadowed.add(value(param))
        if node.type in types and node.start_byte not in top_functions:
            name = _declared_name_node(node, source, parser_language)
            if name: shadowed.add(value(name))
    for node in _walk(root):
        if node.type != 'call_expression': continue
        target = node.child_by_field_name('function')
        name = value(target)
        ancestors = [a for a in _ancestors(node) if a.type in types]
        caller = ancestors[0].start_point[0] + 1 if ancestors else None
        eligible = target is not None and target.type in {'identifier', 'member_expression'} and all(p.isidentifier() for p in name.split('.'))
        eligible = eligible and (not ancestors or ancestors[0].start_byte in top_functions) and name.split('.')[0] not in shadowed and bindings[name.split('.')[0]] == 1
        caller_name = _declared_name_node(ancestors[0], source, parser_language) if ancestors else None
        calls.append({'caller_name': value(caller_name), 'name': name or '<dynamic call>', 'line': node.start_point[0]+1, 'end': node.end_point[0]+1, 'caller': caller, 'eligible': eligible})
    definitions = [d for d in definitions if d['name'] not in shadowed and bindings[d['name']] == 1]
    return {'version': 1, 'definitions': definitions, 'imports': imports, 'calls': calls}
