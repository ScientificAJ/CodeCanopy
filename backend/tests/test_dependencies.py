import json
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.services import snapshot_service as snapshots
from test_v1_workspace import client, import_files


def analyze(client, files):
    path, run, _ = import_files(client, files)
    response = client.get(path + '/dependencies')
    assert response.status_code == 200, response.text
    data = response.json()
    nodes = {n['id']: n for n in data['nodes']}
    edges = [(nodes[e['source_id']]['path'], nodes[e['source_id']]['label'], nodes[e['target_id']]['path'], nodes[e['target_id']]['label'], e['kind']) for e in data['edges']]
    return path, run, data, edges


def test_python_alias_relative_namespace_and_evidence(client):
    path, _, data, edges = analyze(client, {
        'pkg/__init__.py': '', 'pkg/util.py': 'def validate(value):\n    return value\n',
        'pkg/caller.py': 'from .util import validate as check\nfrom . import util\nimport pkg.util as tools\ndef run(x):\n    check(x)\n    util.validate(x)\n    tools.validate(x)\n',
        'main.py': 'import pkg.util\npkg.util.validate(1)\n',
    })
    calls = [e for e in edges if e[-1] == 'calls']
    assert len(calls) == 4, (data, edges)
    assert all(e[2:4] == ('pkg/util.py', 'validate') for e in calls)
    assert data['coverage']['analyzed_files'] == 4
    for edge in data['edges']:
        source = client.get(path + '/source/' + edge['file_id'], params={'line_start': edge['line_start'], 'line_end': edge['line_end']})
        assert source.status_code == 200 and source.json()['content']
    assert client.get(path + '/dependencies').json() == data


def test_shadowed_ambiguous_methods_and_external_are_unresolved(client):
    _, _, data, edges = analyze(client, {
        'util.py': 'def work():\n    pass\n', 'other.py': 'def work():\n    pass\n',
        'main.py': 'from util import work\nimport absent\ndef valid():\n    work()\ndef shadow(work):\n    work()\ndef assigned():\n    work = lambda: 0\n    work()\ndef object_call(obj):\n    obj.work()\n',
        'ambiguous.py': 'from util import work\nfrom other import work\nwork()\n',
        'reassigned.py': 'def work():\n    pass\nwork = lambda: 0\nwork()\n',
        'nested.py': 'from util import work\ndef wrapper():\n    def inner():\n        work()\n',
    })
    assert [e for e in edges if e[-1] == 'calls'] == [('main.py', 'valid', 'util.py', 'work', 'calls')]
    assert data['coverage']['unresolved_count'] >= 6
    assert any(u['name'] == 'absent' and u['kind'] == 'imports' for u in data['unresolved'])


def test_js_ts_named_default_namespace_and_exports(client):
    _, _, data, edges = analyze(client, {
        'src/util.ts': 'export function work(x: number) { return x; }\nexport default function primary() { return 1; }\nfunction hidden() { return 0; }',
        'src/main.ts': 'import primary, {work as run, hidden} from "./util.js";\nimport * as tools from "./util";\nexport function main() {\n run(2);\n primary();\n tools.work(3);\n hidden();\n }',
        'src/component.tsx': 'import {work} from "./util";\nexport const View = () => <p>{work(1)}</p>;',
        'src/index.js': 'export const helper = () => 1;', 'consumer.js': 'import {helper} from "./src"; helper();',
    })
    calls = [e for e in edges if e[-1] == 'calls']
    assert len(calls) == 5, (data, edges)
    assert all(e[3] != 'hidden' for e in calls)
    assert any(u['name'] == 'hidden' for u in data['unresolved'])
    assert data['coverage']['analyzed_files'] == 5


def test_js_shadowing_reexports_dynamic_and_ambiguous_extensions(client):
    _, _, data, edges = analyze(client, {
        'util.js': 'export function run() { return 1; }', 'util.ts': 'export function run() { return 2; }',
        'main.js': 'import {run} from "./util"; run();',
        'shadow.js': 'import {run} from "./util.js"; function f(run) { run(); }',
        'barrel.js': 'export {run} from "./util.js";',
        'consumer.js': 'import {run} from "./barrel.js"; run(); import("./util.js");',
        'member.js': 'import * as util from "./util.js"; util["run"]();',
    })
    assert not [e for e in edges if e[-1] == 'calls']
    assert data['coverage']['unresolved_count'] >= 5


def test_cycles_recursion_and_coverage(client):
    _, _, data, edges = analyze(client, {
        'a.py': 'from b import second\ndef first():\n    second()\n    first()\n',
        'b.py': 'from a import first\ndef second():\n    first()\n',
        'README.md': 'Read me', 'broken.py': 'def !!', '.env': 'SECRET=no', 'blob.bin': b'\x00data',
        'main.go': 'package main\nfunc main() {}',
    })
    assert len([e for e in edges if e[-1] == 'calls']) == 3
    assert data['coverage']['analyzed_files'] == 2 and data['coverage']['unsupported_files'] == 5
    assert not any(n['path'] in {'.env', 'blob.bin'} for n in data['nodes'])


def test_access_expiry_and_legacy_metadata(client):
    path, run, _, _ = analyze(client, {'main.py': 'def f():\n    f()\n'})
    with TestClient(app) as stranger:
        stranger.post('/api/v1/session')
        assert stranger.get(path + '/dependencies').status_code == 404
    assert client.get(path.replace(run['project_id'], '0' * 32) + '/dependencies').status_code == 404
    root = snapshots._v1_root() / run['result_snapshot_id']
    syntax = json.loads((root / 'syntax.json').read_text())
    for item in syntax.values(): item.pop('dependency_syntax')
    (root / 'syntax.json').write_text(json.dumps(syntax))
    legacy = client.get(path + '/dependencies').json()
    assert legacy['coverage']['analyzed_files'] == 0 and not legacy['edges']
    snapshot = json.loads((root / 'snapshot.json').read_text())
    snapshot['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    (root / 'snapshot.json').write_text(json.dumps(snapshot))
    assert client.get(path + '/dependencies').status_code == 410


def test_limits_keep_references_valid(client, monkeypatch):
    from app.features import dependencies
    monkeypatch.setattr(dependencies, 'MAX_NODES', 3)
    monkeypatch.setattr(dependencies, 'MAX_EDGES', 1)
    monkeypatch.setattr(dependencies, 'MAX_UNRESOLVED', 1)
    _, _, data, _ = analyze(client, {'a.py': 'def a():\n    a()\n    print(1)\n    abs(-1)\n', 'b.py': 'from a import a\na()'})
    assert data['coverage']['truncated']
    assert len(data['nodes']) <= 3 and len(data['edges']) <= 1 and len(data['unresolved']) <= 1
    ids = {n['id'] for n in data['nodes']}
    assert all(e['source_id'] in ids and e['target_id'] in ids for e in data['edges'])


def test_less_common_shadowing_and_decorated_targets_are_not_guessed(client):
    _, _, data, edges = analyze(client, {
        'util.py': 'def work():\n    return 1\n',
        'wildcard.py': 'from util import *\ndef work():\n    return 2\nwork()\n',
        'excepts.py': 'from util import work\ndef run():\n    try:\n        pass\n    except Exception as work:\n        work()\n',
        'decorated.py': '@unknown\ndef work():\n    return 1\n',
        'caller.py': 'from decorated import work\nwork()\n',
        'util.js': 'export const work = () => 1;',
        'arrow.js': 'import {work} from "./util.js"; export const run = work => work();',
    })
    assert not [e for e in edges if e[-1] == 'calls'], (data, edges)


def test_functions_on_same_line_keep_correct_definitions_and_callers(client):
    _, _, data, edges = analyze(client, {
        'compact.js': 'export function first() { return 1; } export function second() { return first(); }',
        'caller.js': 'import {first, second} from "./compact.js"; first(); second();',
    })
    calls = [e for e in edges if e[-1] == 'calls']
    assert ('compact.js', 'second', 'compact.js', 'first', 'calls') in calls
    assert ('caller.js', 'caller.js', 'compact.js', 'first', 'calls') in calls
    assert ('caller.js', 'caller.js', 'compact.js', 'second', 'calls') in calls
    assert len({n['id'] for n in data['nodes']}) == len(data['nodes'])


def test_js_callbacks_and_named_expressions_do_not_create_global_bindings(client):
    _, _, data, edges = analyze(client, {
        'main.js': 'const holder = function internal() { return 1; }; internal();\nconst result = invoke(() => 2); result();\nfunction real() { return 3; } real();',
    })
    assert [(e[1], e[3]) for e in edges if e[-1] == 'calls'] == [('main.js', 'real')], (data, edges)
