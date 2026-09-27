"""Deterministic dependency resolution over immutable, sandbox-extracted syntax."""
from collections import defaultdict
import posixpath

from app.models.v1.dependencies import DependencyResult
from app.services.inventory_service import entity_id
from app.services.snapshot_service import get_inventory, get_syntax_records

MAX_NODES = 5000
MAX_EDGES = 15000
MAX_UNRESOLVED = 3000
LIMITATIONS = [
    'Static bindings show possible connections, not proof that a call runs or a change causes a failure.',
    'Resolves Python imports from the repository root and relative imports; resolves JavaScript/TypeScript relative ES imports. Custom source roots, path aliases, package exports and re-exports are not followed.',
    'Function resolution covers unambiguous module-level functions. Dynamic calls, object methods, closures, reassigned and shadowed bindings remain unresolved.',
    'External packages are not downloaded or inspected. Other languages and older snapshots without binding metadata require further analysis; re-import older snapshots to extract bindings.',
]


def analyze(snapshot_id):
    inventory = get_inventory(snapshot_id, limit=10000)
    records = {r.path: r for r in inventory.files if r.is_text and not r.excluded}
    syntax = {item.path: item for item in get_syntax_records(snapshot_id).values()}
    nodes, edges, unresolved = [], [], []
    node_ids, seen_edges = set(), set()
    truncated = inventory.truncated
    unresolved_count = 0
    def add_node(node):
        nonlocal truncated
        if node['id'] in node_ids:
            return True
        if len(nodes) >= MAX_NODES:
            truncated = True
            return False
        nodes.append(node); node_ids.add(node['id']); return True
    for path, rec in sorted(records.items()):
        add_node(dict(id=rec.id, kind='file', label=rec.name, path=path, file_id=rec.id))
    definitions = defaultdict(list)
    function_nodes = {}
    functions_by_line = defaultdict(list)
    for path, parsed in sorted(syntax.items()):
        if path not in records or records[path].id not in node_ids: continue
        for fn in parsed.functions:
            fid = entity_id(snapshot_id, f'{path}:{fn.name}:{fn.line_start}', 'function')
            node = dict(id=fid, kind='function', label=fn.name, path=path, file_id=records[path].id, line_start=fn.line_start, line_end=fn.line_end)
            if add_node(node):
                function_nodes[(path, fn.name, fn.line_start)] = fid
                functions_by_line[(path, fn.line_start)].append(fid)
        data = parsed.dependency_syntax
        if data:
            for definition in data['definitions']:
                fid = function_nodes.get((path, definition['name'], definition['line']))
                if fid:
                    definitions[(path, definition['name'])].append(fid)
                    for name in definition['exports']:
                        if name != definition['name']:
                            definitions[(path, name)].append(fid)
    def module_target(path, module, language):
        if language == 'python':
            level = len(module) - len(module.lstrip('.'))
            if level:
                base = posixpath.dirname(path).split('/') if '/' in path else []
                if level > len(base): return None
                base = base[:len(base) - level + 1]
                name = '/'.join(base + module[level:].split('.')).rstrip('/')
            else: name = module.replace('.', '/')
            candidates = [name + '.py', name + '/__init__.py']
        else:
            if not module.startswith('.'): return None
            name = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            if name.startswith('../') or name.startswith('/'): return None
            candidates = [name] if posixpath.splitext(name)[1] else [name + ext for ext in ('.js', '.jsx', '.ts', '.tsx', '/index.js', '/index.jsx', '/index.ts', '/index.tsx')]
            if name.endswith('.js') and name not in records:
                candidates += [name[:-3] + '.ts', name[:-3] + '.tsx']
        matches = [c for c in candidates if c in records]
        return matches[0] if len(matches) == 1 else None
    def unique_function(path, name, exported=False):
        candidates = definitions.get((path, name), [])
        parsed = syntax.get(path)
        if exported and parsed and parsed.language != 'python':
            data = parsed.dependency_syntax or {}
            allowed = {function_nodes.get((path, d['name'], d['line'])) for d in data.get('definitions', []) if name in d['exports']}
            candidates = [c for c in candidates if c in allowed]
        return candidates[0] if len(candidates) == 1 else None
    def edge(source, target, kind, rec, line, end):
        nonlocal truncated
        key = (source, target, kind, line, end)
        if key in seen_edges: return
        if source not in node_ids or target not in node_ids or len(edges) >= MAX_EDGES:
            truncated = True; return
        seen_edges.add(key)
        edges.append(dict(id=entity_id(snapshot_id, repr(key), 'dependency'), source_id=source, target_id=target, kind=kind, file_id=rec.id, line_start=line, line_end=end))
    def missing(source, name, kind, rec, line, reason):
        nonlocal unresolved_count, truncated
        unresolved_count += 1
        if len(unresolved) >= MAX_UNRESOLVED:
            truncated = True; return
        unresolved.append(dict(source_id=source, name=name[:240], kind=kind, file_id=rec.id, line_start=line, reason=reason))
    analyzed = 0
    for path, parsed in sorted(syntax.items()):
        rec = records.get(path)
        data = parsed.dependency_syntax
        if not rec or rec.id not in node_ids or not data: continue
        analyzed += 1
        bindings = defaultdict(list)
        for imp in data['imports']:
            target = module_target(path, imp['module'], parsed.language)
            symbol = imp['symbol']
            namespace = imp['namespace']
            # `from . import util` and `from package import util` can bind a module.
            if parsed.language == 'python' and symbol and symbol != '*':
                full = imp['module'] + ('' if imp['module'].endswith('.') else '.') + symbol
                submodule = module_target(path, full, parsed.language)
                if submodule and not unique_function(target, symbol):
                    target, symbol, namespace = submodule, None, True
            bindings[imp['local']].append((target, symbol, namespace, imp['prefix']))
            if target:
                edge(rec.id, records[target].id, 'imports', rec, imp['line'], imp['line'])
            else:
                missing(rec.id, imp['module'], 'imports', rec, imp['line'], 'External, missing, ambiguous, or unsupported module path.')
        for call in data['calls']:
            callers = functions_by_line.get((path, call['caller']), [])
            source = function_nodes.get((path, call.get('caller_name'), call['caller']))
            source = source or (callers[0] if len(callers) == 1 else rec.id)
            name = call['name']
            target = None
            if call['eligible']:
                if '.' not in name: target = unique_function(path, name)
                options = bindings.get(name.split('.')[0], [])
                if len(options) == 1:
                    module, symbol, namespace, prefix = options[0]
                    if module:
                        if namespace and name.startswith(prefix + '.') and name[len(prefix)+1:].isidentifier():
                            target = unique_function(module, name[len(prefix)+1:], True)
                        elif not namespace and '.' not in name and symbol:
                            target = unique_function(module, symbol, True)
            if target:
                edge(source, target, 'calls', rec, call['line'], call['end'])
            else:
                missing(source, name, 'calls', rec, call['line'], 'No unambiguous static function binding; may be built-in, external, dynamic, or shadowed.')
    return DependencyResult(snapshot_id=snapshot_id, nodes=nodes, edges=edges, unresolved=unresolved,
        coverage=dict(inventoried_files=len(inventory.files), analyzed_files=analyzed,
                      unsupported_files=len(inventory.files) - analyzed, unresolved_count=unresolved_count,
                      truncated=truncated, limitations=LIMITATIONS))
