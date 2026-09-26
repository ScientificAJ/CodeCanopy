import io
import json
from pathlib import Path
import threading
import time
import urllib.request

import jsonschema
import pytest
from app.services import github_import as github, run_service, snapshot_service
from app.services.retention_service import purge_expired
from test_v1_workspace import client, import_files, zip_bytes


@pytest.mark.parametrize('url', ['http://github.com/a/b', 'https://user:secret@github.com/a/b', 'https://github.com.evil/a/b', 'https://github.com/a/b/tree/main', 'https://github.com/a/b?token=secret', 'https://127.0.0.1/a/b', 'https://github.com/a/..'])
def test_github_url_constraint(url):
    with pytest.raises(github.GitHubImportError): github.parse_github_url(url)


def test_redirect_rejected_before_next_request():
    handler = github.AllowlistedRedirects()
    for target in ['http://github.com/a/b','https://127.0.0.1/secrets','https://api.github.com:443/a','https://user@github.com/a']:
        with pytest.raises(github.GitHubImportError):
            handler.redirect_request(urllib.request.Request('https://api.github.com/repos/a/b'), None,302,'found',{},target)


def test_github_pinning_and_source_survive_staging_cleanup(client, monkeypatch):
    sha = 'b' * 40
    calls = []
    def metadata(url):
        calls.append(url)
        return json.dumps({'private':False,'default_branch':'main'} if url.endswith('/repos/a/repo') else {'sha':sha}).encode()
    monkeypatch.setattr(github,'_safe_urlopen',metadata)
    def download(owner, repo, commit, target, check_cancel):
        assert (owner,repo,commit) == ('a','repo',sha)
        archive = target / 'github.zip'; archive.write_bytes(zip_bytes({'repo-' + sha + '/app.txt':'pinned source'})); return archive
    monkeypatch.setattr(github,'download_archive',download)
    response = client.post('/api/v1/imports/github',json={'url':'https://github.com/a/repo'})
    assert response.status_code == 202
    for _ in range(200):
        run = client.get('/api/v1/runs/' + response.json()['run_id']).json()
        if run['status'] in {'completed','partial','failed'}: break
        time.sleep(.01)
    assert run['status'] == 'completed', run
    base = f"/api/v1/projects/{run['project_id']}/snapshots/{run['result_snapshot_id']}"
    snap = client.get(base).json(); assert snap['source']['resolved_commit'] == sha
    file = client.get(base + '/files').json()['files'][0]; assert file['path'] == 'app.txt'
    assert client.get(base + '/source/' + file['id']).json()['content'] == 'pinned source'
    assert calls[-1].endswith('/commits/main')


def test_cancel_wins_publication_race(client, monkeypatch):
    started = threading.Event(); release = threading.Event()
    original = run_service.create_snapshot_from_project
    def blocked(*args, **kwargs):
        started.set(); assert release.wait(5); return original(*args,**kwargs)
    monkeypatch.setattr(run_service,'create_snapshot_from_project',blocked)
    result = client.post('/api/v1/imports/zip',files={'file':('repo.zip',zip_bytes({'a.txt':'a'}))}).json()
    assert started.wait(5)
    cancelled = client.post('/api/v1/runs/' + result['run_id'] + '/cancel')
    assert cancelled.status_code == 202 and cancelled.json()['status'] == 'cancelled'
    release.set()
    for _ in range(100):
        if result['run_id'] not in run_service._active: break
        time.sleep(.01)
    run = client.get('/api/v1/runs/' + result['run_id']).json()
    assert run['result_snapshot_id'] is None
    assert client.get('/api/v1/projects/' + result['project_id']).status_code == 404


def test_live_graph_and_run_conform_to_versioned_prd(client):
    path, run, _ = import_files(client, {'src/main.py':'value=1'})
    schema = json.loads((Path(__file__).resolve().parents[2] / 'contracts/structure-1.1.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(run)
    jsonschema.Draft202012Validator(schema).validate(client.get(path + '/graph').json())
    grouped = client.get(path + '/view').json()
    entity = client.get(path + '/files').json()['files'][0]
    grouped['groups'] = [{'id':'group_test','label':'Reading','members':[entity['id']]}]
    client.patch(path + '/view',json=grouped)
    artifact = client.post(path + '/map',json={'focus':'group_test'}).json()
    jsonschema.Draft202012Validator(schema).validate(artifact['graph'])
    assert artifact['receipt']['ok'] is True


def test_retention_removes_expired_bytes(client):
    from datetime import datetime,timedelta,timezone
    path, run, _ = import_files(client, {'source.txt':'temporary'})
    root = snapshot_service._v1_root() / run['result_snapshot_id']
    snapshot = json.loads((root / 'snapshot.json').read_text())
    snapshot['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    (root / 'snapshot.json').write_text(json.dumps(snapshot)); purge_expired()
    assert not (root / 'files').exists()
    assert client.get(path).status_code == 410


def test_failed_render_never_returns_last_good_html(client, monkeypatch):
    from app.services import view_service
    path, run, _ = import_files(client, {'file.txt':'hello'})
    assert client.post(path + '/map',json={}).status_code == 200
    prefs = client.get(path + '/view').json(); prefs['theme'] = 'dark'; client.patch(path + '/view',json=prefs)
    class Failure:
        returncode = 1
    monkeypatch.setattr(view_service.subprocess,'run',lambda *a,**kw: Failure())
    response = client.post(path + '/map',json={})
    assert response.status_code == 422 and 'html' not in response.json()


@pytest.mark.parametrize('count',[0,1,2,3])
def test_every_compiler_chapter_size_is_valid(client, count):
    path, _, _ = import_files(client, {f'src/file{i}.txt':'text' for i in range(max(1,count))})
    if count == 0:
        preferences = client.get(path + '/view').json()
        preferences['groups'] = [{'id':'group_empty','label':'Empty group','members':[]}]
        client.patch(path + '/view',json=preferences)
        focus = 'group_empty'
    else:
        focus = 'src'
    response = client.post(path + '/map',json={'focus':focus})
    assert response.status_code == 200, response.text
    receipt = response.json()['receipt']
    assert receipt['ok']
    assert receipt['validation'] == {
        'checkCount': 9, 'checksPassed': 9, 'compositionProfile': 'showcase',
        'compositionStatus': 'pass', 'errors': 0, 'warnings': 0,
    }
    import re
    html = response.json()['html']
    manifest = json.loads(re.search(r'<script id="codecanopy-manifest" type="application/json">(.*?)</script>', html).group(1))
    assert manifest['validation']['checksPassed'] == 9
    assert manifest['validation']['upstream_sha256'] == receipt['artifact']['sha256']
    assert 'Copyright (c) 2026 tt-a1i (Archify)' in html
    assert 'Copyright (c) 2025 Cocoon AI' in html
