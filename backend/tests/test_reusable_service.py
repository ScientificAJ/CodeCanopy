"""Reuse regressions through real snapshot imports and authenticated endpoints."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.features.reusable_functions import ConcreteReusableFunctionService, ReusableFunctionRequest
from app.services.snapshot_service import create_snapshot_from_project, _v1_root
from app.services.v1_errors import WorkspaceError
from test_v1_workspace import client, import_files  # noqa: F401


def analyze(tmp_path, monkeypatch, files, min_callers=1):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    source = tmp_path / 'source'
    source.mkdir()
    for name, text in files.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    snap, _ = create_snapshot_from_project('a' * 32, source, 'test', 'review')
    result = asyncio.run(ConcreteReusableFunctionService().execute(
        ReusableFunctionRequest(snapshot_id=snap.id, min_callers=min_callers)))
    return snap, result


@pytest.mark.parametrize('files', [
    {'a.py': 'def helper():\n    return 1\n', 'b.py': 'from a import helper\nhelper()\n'},
    {'a.js': 'export function helper() { return 1; }', 'b.js': 'import {helper} from "./a.js";\nhelper();'},
    {'a.ts': 'export function helper(): number { return 1; }', 'b.ts': 'import {helper} from "./a";\nhelper();'},
    {'A.java': 'class A { static int helper() { return 1; } }', 'B.java': 'class B { int run() { return A.helper(); } }'},
])
def test_real_import_extracts_cross_file_calls(tmp_path, monkeypatch, files):
    _, result = analyze(tmp_path, monkeypatch, files)
    assert result.analyzed_files == 2
    assert result.total_reusable == 1
    group = result.groups[0]
    assert group.function_name == 'helper'
    assert group.defined_file_id and group.call_sites[0].file_id
    assert group.call_sites[0].line_start >= 1
    assert group.called_from == [list(files)[1]]


def test_same_name_local_helpers_are_not_cross_file_reuse(tmp_path, monkeypatch):
    code = 'def helper():\n    return 1\n\ndef run():\n    return helper()\n'
    _, result = analyze(tmp_path, monkeypatch, {'a.py': code, 'z.py': code})
    assert result.total_reusable == 0
    assert result.ambiguous_names == 2


def test_different_languages_do_not_share_call_names(tmp_path, monkeypatch):
    _, result = analyze(tmp_path, monkeypatch, {'a.py': 'def helper(): pass', 'b.js': 'helper();'})
    assert result.total_reusable == 0


def test_comments_strings_and_definitions_are_not_calls(tmp_path, monkeypatch):
    _, result = analyze(tmp_path, monkeypatch, {
        'a.js': 'export function helper() {}',
        'b.js': '// helper();\nconst text = "helper()";',
    })
    assert result.total_reusable == 0


def test_min_callers_counts_distinct_files(tmp_path, monkeypatch):
    _, result = analyze(tmp_path, monkeypatch, {
        'a.py': 'def helper(): pass', 'b.py': 'helper()\nhelper()\n',
    }, min_callers=2)
    assert result.total_reusable == 0


def test_old_snapshot_reports_missing_call_evidence(tmp_path, monkeypatch):
    snap, _ = analyze(tmp_path, monkeypatch, {'a.py': 'def helper(): pass', 'b.py': 'helper()'})
    path = _v1_root() / snap.id / 'syntax.json'
    data = json.loads(path.read_text())
    for file in data.values():
        file.pop('call_sites')
    path.write_text(json.dumps(data))
    result = asyncio.run(ConcreteReusableFunctionService().execute(ReusableFunctionRequest(snapshot_id=snap.id)))
    assert result.analyzed_files == 0 and result.total_reusable == 0
    assert any('Import the repository again' in item for item in result.limitations)


def test_missing_syntax_is_an_error(tmp_path, monkeypatch):
    snap, _ = analyze(tmp_path, monkeypatch, {'a.py': 'def helper(): pass'})
    (_v1_root() / snap.id / 'syntax.json').unlink()
    with pytest.raises(WorkspaceError, match='unavailable'):
        asyncio.run(ConcreteReusableFunctionService().execute(ReusableFunctionRequest(snapshot_id=snap.id)))


def test_reuse_api_preserves_access_boundaries_and_other_findings(client):
    path, run, _ = import_files(client, {
        'a.py': 'def helper():\n    return 1\n\ndef orphan():\n    return 1\n',
        'b.py': 'from a import helper\nhelper()\n',
    })
    response = client.get(path + '/findings/reuse')
    assert response.status_code == 200, response.text
    result = response.json()
    group = result['groups'][0]
    assert group['function_name'] == 'helper'
    source = client.get(path + '/source/' + group['defined_file_id'], params={'line_start': group['defined_line_start'], 'line_end': group['defined_line_end']})
    assert source.status_code == 200 and 'def helper' in source.json()['content']
    assert client.get(path + '/reusable-functions').json() == result
    assert client.get(path + '/findings/reuse?min_callers=0').status_code == 422
    assert client.get(path + '/findings/duplicates').status_code == 200
    assert client.get(path + '/findings/unused').status_code == 200
    assert client.get(path.replace(run['project_id'], '0' * 32) + '/findings/reuse').status_code == 404
    with TestClient(app) as stranger:
        stranger.post('/api/v1/session')
        assert stranger.get(path + '/findings/reuse').status_code == 404
    metadata = _v1_root() / run['result_snapshot_id'] / 'snapshot.json'
    data = json.loads(metadata.read_text())
    data['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    metadata.write_text(json.dumps(data))
    assert client.get(path + '/findings/reuse').status_code == 410
