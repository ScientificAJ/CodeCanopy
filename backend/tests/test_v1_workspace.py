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


def test_archify_export_and_view_isolation(client):
    path, run, _ = import_files(client, {'a/a.py': 'x=1', 'b/b.js': 'x=2', 'c/c.txt': 'three', 'd.txt': 'four'})
    inventory = client.get(path + '/files').json()
    entities = client.get(path + '/entities').json()
    result = client.post(path + '/map', json={})
    assert result.status_code == 200, result.text
    artifact = result.json()
    assert len(artifact['graph']['entities']) == 4
    assert artifact['graph']['next_cursor'] == 3
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
