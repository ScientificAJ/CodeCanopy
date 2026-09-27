"""Hosted request consolidation must retain fresh ownership and full coverage."""
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.v1.session import COOKIE
from app.main import app
from app.services import cloud_storage as cloud, snapshot_service as snapshots
from test_cloud_storage import MemoryBlob


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('CODECANOPY_STORAGE', 'vercel_blob')
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    sdk = MemoryBlob()
    monkeypatch.setattr(cloud, '_sdk', lambda: sdk)
    with TestClient(app) as client:
        client.post('/api/v1/session')
        owner = hashlib.sha256(client.cookies.get(COOKIE).encode()).hexdigest()
        source = tmp_path / 'source'; source.mkdir()
        (source / 'README.md').write_text('A full repository.\n')
        (source / 'main.py').write_text('def useful_function():\n    return 42\n')
        snap, _ = snapshots.create_snapshot_from_project('1' * 32, source, 'digest', 'Example', workspace_id=owner)
        sdk.reads.clear()
        yield client, sdk, snap, owner
    snapshots._cached_inventory.cache_clear()
    snapshots._cached_syntax.cache_clear()
    snapshots._syntax_index.cache_clear()


def base(snap):
    return f'/api/v1/projects/{snap.project_id}/snapshots/{snap.id}'


def test_bootstrap_consolidates_authorization_without_losing_inventory(workspace):
    client, sdk, snap, owner = workspace
    response = client.get(base(snap) + '/bootstrap')
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['project']['name'] == 'Example'
    assert payload['snapshot']['id'] == snap.id
    assert payload['files']['total'] == 2 and payload['files']['cursor'] is None
    assert {r['path'] for r in payload['files']['files']} == {'main.py', 'README.md'}
    assert len(payload['entities']) == 3
    assert payload['capabilities']['parsed_count'] == 1
    assert payload['preferences']['focus'] == '.'
    assert sdk.reads.count(cloud._item(owner, 'projects', snap.project_id)) == 1
    assert response.headers['cache-control'] == 'no-store'
    assert 'workspace_id' not in response.text


def test_bootstrap_refuses_strangers_and_revoked_warm_cache(workspace):
    client, sdk, snap, owner = workspace
    assert client.get(base(snap) + '/bootstrap').status_code == 200
    with TestClient(app) as stranger:
        stranger.post('/api/v1/session')
        assert stranger.get(base(snap) + '/bootstrap').status_code == 404
    sdk.objects.pop(cloud._item(owner, 'projects', snap.project_id))
    assert client.get(base(snap) + '/bootstrap').status_code == 404


def test_oversized_bootstrap_explicitly_falls_back_to_individual_resources(workspace, monkeypatch):
    from app.api.v1 import snapshots as routes
    client, _, snap, _ = workspace
    monkeypatch.setattr(routes, 'MAX_BOOTSTRAP_BYTES', 32)
    result = client.get(base(snap) + '/bootstrap')
    assert result.status_code == 413
    assert result.json()['error']['code'] == 'BOOTSTRAP_TOO_LARGE'
    assert client.get(base(snap) + '/files').json()['total'] == 2


def test_hosted_responses_expose_duration_without_response_or_source_data(workspace, monkeypatch):
    client, _, snap, _ = workspace
    monkeypatch.setenv('VERCEL', '1')
    response = client.get(base(snap) + '/bootstrap')
    assert response.status_code == 200
    timing = response.headers['server-timing']
    assert timing.startswith('app;dur=') and float(timing.split('=')[1]) >= 0


def test_blob_client_reuses_one_thread_safe_pool(monkeypatch):
    import vercel.blob
    clients, shutdowns = [], []
    class Client:
        def __init__(self): clients.append(self)
        def close(self): pass
    monkeypatch.setattr(cloud, '_blob_client', None)
    monkeypatch.setattr(vercel.blob, 'BlobClient', Client)
    monkeypatch.setattr(cloud.atexit, 'register', lambda callback: shutdowns.append(callback))
    with ThreadPoolExecutor(max_workers=8) as executor:
        actual = list(executor.map(lambda _: cloud._sdk(), range(32)))
    assert len(clients) == len(shutdowns) == 1
    assert all(client is clients[0] for client in actual)


def test_recent_import_reads_use_bounded_parallel_origin_checks(monkeypatch):
    owner = 'a' * 64
    sdk = MemoryBlob()
    monkeypatch.setattr(cloud, '_sdk', lambda: sdk)
    expected = []
    for i in range(6):
        pid = f'{i:032x}'; expected.append(pid)
        sdk.objects[cloud._item(owner, 'projects', pid)] = json.dumps({
            'id': pid, 'workspace_id': owner, 'created_at': datetime.now(timezone.utc).isoformat(),
        }).encode()
    real_get = sdk.get
    barrier = threading.Barrier(6)
    def coordinated_get(path, **options):
        barrier.wait(timeout=3)
        return real_get(path, **options)
    monkeypatch.setattr(sdk, 'get', coordinated_get)
    assert [project['id'] for project in cloud.list_projects(owner)] == expected
    assert len(sdk.reads) == 6
