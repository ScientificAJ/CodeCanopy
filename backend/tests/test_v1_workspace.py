import hashlib
import io
import json
import time
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import snapshot_service as snapshots


def zip_bytes(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for path, contents in files.items():
            archive.writestr(path, contents)
    return output.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    with TestClient(app) as client:
        assert client.post('/api/v1/session').status_code == 200
        yield client


def import_files(client, files):
    data = zip_bytes(files)
    accepted = client.post('/api/v1/imports/zip', files={'file': ('example.zip', data, 'application/zip')})
    assert accepted.status_code == 202, accepted.text
    run_id = accepted.json()['run_id']
    for _ in range(300):
        run = client.get('/api/v1/runs/' + run_id).json()
        if run['status'] in {'completed', 'partial', 'failed', 'cancelled'}:
            break
        time.sleep(.02)
    assert run['status'] in {'completed', 'partial'}, run
    path = f"/api/v1/projects/{run['project_id']}/snapshots/{run['result_snapshot_id']}"
    return path, run, data


def test_inventory_source_identity_policy_and_session(client):
    path, run, archive = import_files(client, {'src/app.py': 'def hello():\n    return 1\n', 'readme.unknown': 'héllo\nworld\n', 'broken.py': 'def !!', 'image.png': b'\0binary', '.env': 'TOKEN=secret', 'unsafe.svg': '<script>alert(1)</script>'})
    snapshot = client.get(path).json()
    assert snapshot['source']['archive_digest'] == hashlib.sha256(archive).hexdigest()
    records = {f['path']: f for f in client.get(path + '/files').json()['files']}
    caps = client.get(path + '/capabilities').json()
    assert run['status'] == 'partial' and caps['parsed_count'] == 1
    assert records['.env']['excluded']
    assert client.get(path + '/source/' + records['.env']['id']).status_code == 403
    assert client.get(path + '/source/' + records['image.png']['id']).status_code == 415
    file = records['readme.unknown']
    source = client.get(path + '/source/' + file['id'] + '?line_start=2&max_lines=1').json()
    assert source['content'] == 'world' and source['line_start'] == source['line_end'] == 2
    assert source['content_hash'] == file['content_hash']
    assert client.get(path + '/source/' + file['id'] + '?line_start=99').status_code == 422
    entities = client.get(path + '/entities').json()
    assert next(e for e in entities if e['path'] == file['path'])['id'] == file['id']
    assert client.get(path + '/summaries').status_code == 501
    with TestClient(app) as stranger:
        stranger.post('/api/v1/session')
        assert stranger.get(path).status_code == 404
        assert stranger.get('/api/v1/runs/' + run['id']).status_code == 404
    assert client.get(path, headers={'Origin': 'https://evil.test'}).status_code == 403
    target = snapshots._v1_root() / snapshot['id'] / 'files' / file['path']
    target.chmod(0o644); target.write_text('tampered')
    assert client.get(path + '/source/' + file['id']).status_code == 409


def test_expiry_and_wrong_project(client):
    path, run, _ = import_files(client, {'app.txt': 'hi'})
    assert client.get(path.replace(run['project_id'], '0' * 32)).status_code == 404
    target = snapshots._v1_root() / run['result_snapshot_id'] / 'snapshot.json'
    value = json.loads(target.read_text()); value['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    target.write_text(json.dumps(value))
    assert client.get(path).status_code == 410


def test_duplicate_and_potentially_unused_findings(client):
    source = '''def validate_email(value):
    return "@" in value

def is_valid_email(address):
    return "@" in address

def check_email(candidate):
    return "@" in candidate

def send_email(address):
    return validate_email(address)

def orphaned_helper(value):
    return value.strip()
'''
    path, _, _ = import_files(client, {'src/validators.py': source})

    duplicates = client.get(path + '/findings/duplicates')
    assert duplicates.status_code == 200, duplicates.text
    payload = duplicates.json()
    assert payload['candidates']
    candidate_names = {function['name'] for function in payload['candidates'][0]['functions']}
    assert candidate_names <= {'validate_email', 'is_valid_email', 'check_email'}
    assert payload['candidates'][0]['structural_similarity'] == 1
    assert any('Semantic comparison is not configured' in item for item in payload['coverage']['limitations'])

    unused = client.get(path + '/findings/unused')
    assert unused.status_code == 200, unused.text
    findings = unused.json()['findings']
    orphan = next(item for item in findings if item['function']['name'] == 'orphaned_helper')
    assert orphan['status'] == 'potentially_unused'
    assert 'potentially' in orphan['status']
    assert all(item['function']['name'] != 'validate_email' for item in findings)


def test_duplicate_findings_use_configured_semantic_provider(client, monkeypatch):
    from app.features.duplicate_detection import analysis

    class StubProvider:
        cache_key = 'test-provider:model'

        async def score_pairs(self, pairs):
            assert len(pairs) == 1
            assert 'return "@" in value' in pairs[0]['code_a']
            return [0.94]

    monkeypatch.setattr(analysis, 'configured_provider', StubProvider)
    source = 'def validate_email(value):\n    return "@" in value\n\ndef is_valid_email(address):\n    return "@" in address\n'
    path, _, _ = import_files(client, {'src/validators.py': source})

    response = client.get(path + '/findings/duplicates')

    assert response.status_code == 200, response.text
    candidate = response.json()['candidates'][0]
    assert candidate['semantic_similarity'] == 0.94
    assert candidate['method'] == 'normalized_ast_structure_and_ai_semantic_comparison'


def test_findings_cover_javascript_and_go_repositories(client):
    javascript = '''function validateEmail(value) { return value.includes("@"); }
function isValidEmail(address) { return address.includes("@"); }
function normalizeEmail(value) { return value.trim(); }
function callNormalize(value) { return normalizeEmail(value); }
function orphanedJs(value) { return value.toLowerCase(); }
function callback(isValidEmail) { return true; }
'''
    go = '''package validation
func validateEmail(value string) bool { return strings.Contains(value, "@") }
func isValidEmail(address string) bool { return strings.Contains(address, "@") }
func normalizeValue(value string) string { return strings.TrimSpace(value) }
func callNormalize(value string) string { return normalizeValue(value) }
func orphanedGo(value string) string { return strings.ToLower(value) }
'''
    sql = '''CREATE FUNCTION numeric_helper(value INT) RETURNS INT AS $$ SELECT value + 1; $$ LANGUAGE SQL;
CREATE FUNCTION used_sql(value INT) RETURNS INT AS $$ SELECT numeric_helper(value); $$ LANGUAGE SQL;
CREATE FUNCTION orphanedSql(value INT) RETURNS INT AS $$ SELECT value + 2; $$ LANGUAGE SQL;
'''
    path, _, _ = import_files(client, {
        'src/validate.js': javascript,
        'src/validate.go': go,
        'src/helpers.sql': sql,
    })

    duplicates = client.get(path + '/findings/duplicates')
    assert duplicates.status_code == 200, duplicates.text
    payload = duplicates.json()
    assert payload['coverage']['parsed_files'] == 3
    assert any('javascript' in limitation and 'go' in limitation and 'sql' in limitation for limitation in payload['coverage']['limitations'])
    capabilities = client.get(path + '/capabilities').json()
    assert {item['parser_name'] for item in capabilities['files'] if item['syntax_extraction']} == {'tree-sitter'}
    candidate_names = [
        {function['name'] for function in candidate['functions']}
        for candidate in payload['candidates']
    ]
    assert {'validateEmail', 'isValidEmail'} in candidate_names

    unused = client.get(path + '/findings/unused')
    assert unused.status_code == 200, unused.text
    names = {finding['function']['name'] for finding in unused.json()['findings']}
    assert {'orphanedJs', 'orphanedGo', 'isValidEmail', 'orphanedSql'} <= names
    assert 'normalizeEmail' not in names
    assert 'normalizeValue' not in names
    assert 'numeric_helper' not in names


def test_archify_export_and_view_isolation(client):
    path, run, _ = import_files(client, {'a/a.py': 'x=1', 'b/b.js': 'x=2', 'c/c.txt': 'three', 'd.txt': 'four'})
    inventory = client.get(path + '/files').json()
    entities = client.get(path + '/entities').json()
    result = client.post(path + '/map', json={})
    assert result.status_code == 200, result.text
    artifact = result.json()
    assert len(artifact['graph']['entities']) == 5
    assert artifact['graph']['next_cursor'] is None
    compact = client.post(path + '/map', json={'page_size':3}).json()
    assert len(compact['graph']['entities']) == 4 and compact['graph']['next_cursor'] == 3
    assert 'Archify.view' in artifact['html'] and 'codecanopy-manifest' in artifact['html']
    assert hashlib.sha256(artifact['html'].encode()).hexdigest() == artifact['html_sha256']
    assert client.post(path + '/map', json={}).json()['html_sha256'] == artifact['html_sha256']
    prefs = client.get(path + '/view').json()
    prefs['labels'][entities[1]['id']] = '</script><script>alert(1)</script>'
    prefs['groups'] = [{'id': 'group_test', 'label': 'My view', 'members': [inventory['files'][0]['id']]}]
    assert client.patch(path + '/view', json=prefs).status_code == 200
    grouped = client.post(path + '/map', json={'focus': 'group_test'})
    assert grouped.status_code == 200, grouped.text
    assert grouped.json()['graph']['relations'][0]['kind'] == 'groups'
    assert client.get(path + '/files').json() == inventory
    assert client.post(path + '/map', json={'focus': 'missing'}).status_code == 404
    prefs['groups'][0]['members'] = ['not-in-snapshot']
    assert client.patch(path + '/view', json=prefs).status_code == 422


@pytest.mark.parametrize('path', ['../escape', '/absolute', 'CON', 'a/../../b'])
def test_v1_rejects_unsafe_zip(client, path):
    response = client.post('/api/v1/imports/zip', files={'file': ('bad.zip', zip_bytes({path: 'bad'}))})
    assert response.status_code == 202
    for _ in range(100):
        result = client.get('/api/v1/runs/' + response.json()['run_id']).json()
        if result['status'] == 'failed': break
        time.sleep(.01)
    assert result['status'] == 'failed'
    assert result['result_snapshot_id'] is None


def test_group_edit_colors_density_and_pagination_preserve_source(client):
    path, _, _ = import_files(client, {f'src/file{i:03}.txt': f'content {i}' for i in range(20)})
    inventory = client.get(path + '/files').json()
    ids = [f['id'] for f in inventory['files']]
    preferences = client.get(path + '/view').json()
    preferences.update(density='expanded', groups=[{'id':'group_reading','label':'Reading','members':ids[:3],'color':'blue'}])
    assert client.patch(path + '/view', json=preferences).status_code == 200
    preferences['groups'][0].update(label='Upload review', color='violet', members=ids[1:3])
    response = client.patch(path + '/view', json=preferences)
    assert response.status_code == 200 and response.json()['groups'][0]['members'] == ids[1:3]
    graph = client.post(path + '/map', json={'focus':'group_reading'}).json()['graph']
    assert graph['entities'][0]['label'] == 'Upload review'
    assert graph['entities'][0]['metadata']['group_color'] == 'violet'
    first = client.post(path + '/map', json={'focus':'src','page_size':8}).json()['graph']
    second = client.post(path + '/map', json={'focus':'src','cursor':8,'page_size':8}).json()['graph']
    assert first['child_total'] == 20 and first['next_cursor'] == 8 and second['next_cursor'] == 16
    assert not ({e['id'] for e in first['entities'][1:]} & {e['id'] for e in second['entities'][1:]})
    assert client.get(path + '/files').json() == inventory
    preferences['groups'][0]['color'] = 'url(javascript:bad)'
    assert client.patch(path + '/view', json=preferences).status_code == 422
    assert client.post(path + '/map', json={'page_size':100000}).status_code == 422
