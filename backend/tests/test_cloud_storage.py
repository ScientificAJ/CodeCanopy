"""Hosted workspaces survive instance replacement without sharing local files."""
import io
import json
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from app.services import cloud_storage as cloud, snapshot_service as snapshots
from app.services.v1_errors import WorkspaceError

WORKSPACE, OTHER_WORKSPACE, PROJECT = 'a' * 64, 'b' * 64, '1' * 32

class MemoryBlob:
    def __init__(self):
        self.objects, self.reads, self.fail_path = {}, [], None
    def put(self, path, body, **options):
        assert options['access'] == 'private' and options['add_random_suffix'] is False
        if self.fail_path and self.fail_path in path:
            raise RuntimeError('provider error with secret must never escape')
        if not options['overwrite'] and path in self.objects:
            raise RuntimeError('already exists')
        self.objects[path] = body.read() if hasattr(body, 'read') else body
    def get(self, path, **options):
        assert options['access'] == 'private' and options['use_cache'] is False
        self.reads.append(path)
        if path not in self.objects:
            from vercel.blob.errors import BlobNotFoundError
            raise BlobNotFoundError()
        return SimpleNamespace(content=self.objects[path])
    def delete(self, paths):
        for path in paths:
            self.objects.pop(path, None)
    def list_objects(self, *, prefix, cursor=None, limit=None):
        items = [SimpleNamespace(pathname=path, uploaded_at=datetime.now(timezone.utc))
                 for path in sorted(self.objects) if path.startswith(prefix)]
        return SimpleNamespace(blobs=items, cursor=None, has_more=False)

@pytest.fixture
def hosted(tmp_path, monkeypatch):
    monkeypatch.setenv('CODECANOPY_STORAGE', 'vercel_blob')
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'instance-one'))
    sdk = MemoryBlob()
    monkeypatch.setattr(cloud, '_sdk', lambda: sdk)
    yield sdk
    snapshots._cached_inventory.cache_clear()
    snapshots._cached_syntax.cache_clear()
    snapshots._syntax_index.cache_clear()

def publish(tmp_path):
    source = tmp_path / 'source'; source.mkdir(exist_ok=True)
    (source / 'README.md').write_text('A durable repository.\nSecond line.\n')
    (source / '.env').write_text('SECRET=must-not-store-source')
    return snapshots.create_snapshot_from_project(PROJECT, source, 'digest', 'Example', workspace_id=WORKSPACE)

def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'instance-two'))

def test_snapshot_survives_instance_loss_and_enforces_workspace(hosted, tmp_path, monkeypatch):
    snap, records = publish(tmp_path)
    shutil.rmtree(snapshots._v1_root()); fresh(tmp_path, monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        snapshots.authorized_snapshot(PROJECT, snap.id, OTHER_WORKSPACE)
    assert error.value.status == 404
    assert snapshots.authorized_snapshot(PROJECT, snap.id, WORKSPACE).id == snap.id
    record = next(record for record in records if record.path == 'README.md')
    assert snapshots.read_source_text(snap.id, record.id)[1] == 'A durable repository.\nSecond line.\n'
    assert not (snapshots._v1_root() / snap.id / 'files' / '.env').exists()
    assert snapshots.get_project(PROJECT).name == 'Example'
    assert [project.id for project in snapshots.list_projects(WORKSPACE)] == [PROJECT]
    assert snapshots.list_projects(OTHER_WORKSPACE) == []

def test_deletion_revokes_even_warm_instance_access(hosted, tmp_path, monkeypatch):
    snap, _ = publish(tmp_path); first_root = snapshots._v1_root()
    fresh(tmp_path, monkeypatch); snapshots.delete_project(PROJECT, WORKSPACE)
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(first_root))
    assert (first_root / snap.id / 'snapshot.json').exists()
    with pytest.raises(WorkspaceError) as error:
        snapshots.authorized_snapshot(PROJECT, snap.id, WORKSPACE)
    assert error.value.status == 404 and not hosted.objects

def test_parallel_hydration_publishes_complete_cache_once(hosted, tmp_path, monkeypatch):
    snap, _ = publish(tmp_path); fresh(tmp_path, monkeypatch); root = snapshots._v1_root()
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: cloud.hydrate_snapshot(snap.id, root), range(8)))
    assert hosted.reads.count(cloud._snapshot(snap.id, 'source.zip')) == 1
    assert (root / snap.id / 'inventory.json').is_file()
    assert not list(root.glob('*.hydrate-*'))

def test_tampered_bundle_is_rejected(hosted, tmp_path, monkeypatch):
    snap, _ = publish(tmp_path)
    hosted.objects[cloud._snapshot(snap.id, 'source.zip')] = b'tampered'; fresh(tmp_path, monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        snapshots.authorized_snapshot(PROJECT, snap.id, WORKSPACE)
    assert error.value.code == 'SOURCE_INTEGRITY'
    assert not (snapshots._v1_root() / snap.id).exists()

@pytest.mark.parametrize('cold', [False, True])
def test_expiry_removes_remote_source_and_returns_410(hosted, tmp_path, monkeypatch, cold):
    snap, _ = publish(tmp_path); key = cloud._snapshot(snap.id, 'snapshot.json')
    descriptor = json.loads(hosted.objects[key])
    descriptor['snapshot']['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    hosted.objects[key] = json.dumps(descriptor).encode()
    (snapshots._v1_root() / snap.id / 'snapshot.json').write_text(json.dumps(descriptor['snapshot']))
    if cold: fresh(tmp_path, monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        snapshots.authorized_snapshot(PROJECT, snap.id, WORKSPACE)
    assert error.value.status == 410
    assert cloud._snapshot(snap.id, 'source.zip') not in hosted.objects and key in hosted.objects

def test_run_and_view_records_are_fresh_and_scoped(hosted):
    run_id, sid = '2' * 32, '3' * 32
    cloud.save_run(WORKSPACE, run_id, {'id': run_id, 'status': 'running'})
    assert cloud.load_run(OTHER_WORKSPACE, run_id) is None
    cloud.save_run(WORKSPACE, run_id, {'id': run_id, 'status': 'completed'})
    assert cloud.load_run(WORKSPACE, run_id)['status'] == 'completed'
    assert cloud.load_view(sid) is None
    cloud.save_view(sid, {'focus': 'src'}); assert cloud.load_view(sid) == {'focus': 'src'}

def test_failed_publication_leaves_no_project_or_snapshot(hosted, tmp_path):
    hosted.fail_path = '/projects/'
    with pytest.raises(WorkspaceError) as error: publish(tmp_path)
    assert error.value.code == 'STORAGE_UNAVAILABLE' and 'secret' not in str(error.value)
    assert hosted.objects == {}
    assert not list(snapshots._v1_root().glob('project_*.json'))
    assert not [path for path in snapshots._v1_root().iterdir() if path.is_dir()]

def test_archive_path_traversal_is_rejected(tmp_path):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive: archive.writestr('../outside.txt', 'bad')
    with pytest.raises(ValueError): cloud._extract_bundle(output.getvalue(), tmp_path / 'hydrate')
    assert not (tmp_path / 'outside.txt').exists()

def test_hosted_mode_fails_closed_without_durable_storage(monkeypatch):
    monkeypatch.delenv('CODECANOPY_STORAGE', raising=False); monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(WorkspaceError) as error: cloud.enabled()
    assert error.value.code == 'STORAGE_UNAVAILABLE'

def test_expiry_cleanup_removes_old_tombstone(hosted, tmp_path):
    snap, _ = publish(tmp_path); key = cloud._snapshot(snap.id, 'snapshot.json')
    descriptor = json.loads(hosted.objects[key])
    descriptor['snapshot']['expires_at'] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    hosted.objects[key] = json.dumps(descriptor).encode()
    assert cloud.purge_expired() == 1 and hosted.objects == {}


def test_cancellation_marker_survives_progress_writes(hosted):
    run_id = '4' * 32
    assert not cloud.cancellation_requested(WORKSPACE, run_id)
    cloud.request_cancel(WORKSPACE, run_id)
    cloud.request_cancel(WORKSPACE, run_id)
    cloud.save_run(WORKSPACE, run_id, {'id': run_id, 'status': 'running'})
    assert cloud.cancellation_requested(WORKSPACE, run_id)
    assert not cloud.cancellation_requested(OTHER_WORKSPACE, run_id)


def test_remote_upload_ownership_checked_before_access(hosted, tmp_path):
    with pytest.raises(WorkspaceError) as error:
        cloud.RemoteBlobArchive(f'uploads/{OTHER_WORKSPACE}/{"3" * 32}.zip', WORKSPACE, tmp_path)
    assert error.value.status == 404
    with pytest.raises(WorkspaceError):
        cloud.RemoteBlobArchive(f'uploads/{WORKSPACE}/../elsewhere.zip', WORKSPACE, tmp_path)


def test_range_reader_extracts_zip_without_downloading_ignored_payload(monkeypatch, tmp_path):
    import httpx
    import os
    from app.services.project_archive import _validated_entries, _extract_entries
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as zip_file:
        zip_file.writestr('node_modules/large.bin', os.urandom(6 * 1024 * 1024))
        zip_file.writestr('README.md', 'Only retained source is extracted.')
    raw = archive.getvalue(); requests = []
    def handle(request):
        assert request.headers['Authorization'] == 'Bearer test-token'
        start, end = map(int, request.headers['Range'].removeprefix('bytes=').split('-'))
        requests.append((start, end))
        return httpx.Response(206, headers={'Content-Range': f'bytes {start}-{end}/{len(raw)}', 'ETag': 'unchanged'}, content=raw[start:end + 1])
    client = httpx.Client(transport=httpx.MockTransport(handle), headers={'Authorization': 'Bearer test-token'})
    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN', 'test-token')
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: client)
    with cloud._BlobRangeReader('https://example.private.blob.vercel-storage.com/file.zip', len(raw)) as reader:
        with zipfile.ZipFile(reader) as zip_file:
            _extract_entries(zip_file, _validated_entries(zip_file), tmp_path / 'retained')
    assert (tmp_path / 'retained' / 'README.md').read_text() == 'Only retained source is extracted.'
    assert not (tmp_path / 'retained' / 'node_modules').exists()
    assert sum(end - start + 1 for start, end in requests) < 2 * 1024 * 1024


def test_range_reader_rejects_server_ignoring_range(monkeypatch):
    import httpx
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b'unbounded')))
    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN', 'test-token')
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: client)
    with cloud._BlobRangeReader('https://example.private.blob.vercel-storage.com/file.zip', 100) as reader:
        with pytest.raises(WorkspaceError) as error:
            reader.read(10)
    assert error.value.status == 503


def test_direct_upload_api_imports_and_removes_staged_blob(hosted, tmp_path, monkeypatch):
    import hashlib
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1.session import COOKIE
    with TestClient(app) as client:
        assert client.post('/api/v1/session').status_code == 200
        workspace = hashlib.sha256(client.cookies.get(COOKIE).encode()).hexdigest()
        pathname = f'uploads/{workspace}/{"5" * 32}.zip'
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('README.md', 'Remote repository')
        raw = payload.getvalue()
        hosted.objects[pathname] = raw
        monkeypatch.setattr(hosted, 'head', lambda path: SimpleNamespace(pathname=path, size=len(raw), url='https://example.private.blob.vercel-storage.com/upload.zip'), raising=False)
        monkeypatch.setattr(cloud, '_BlobRangeReader', lambda url, size: io.BytesIO(raw))
        accepted = client.post('/api/v1/imports/blob', json={'pathname': pathname, 'name': 'remote.zip'})
        assert accepted.status_code == 202, accepted.text
        assert pathname not in hosted.objects
        fresh(tmp_path, monkeypatch)
        run = client.get('/api/v1/runs/' + accepted.json()['run_id'])
        assert run.status_code == 200, run.text
        assert run.json()['status'] in {'completed', 'partial'}, run.text
        projects = client.get('/api/v1/projects').json()
        assert len(projects) == 1 and projects[0]['name'] == 'remote'
        snap = snapshots.authorized_snapshot(run.json()['project_id'], run.json()['result_snapshot_id'], workspace)
        assert snap.source.archive_digest is None


def test_direct_upload_size_is_checked_without_fetching_body(hosted, tmp_path, monkeypatch):
    monkeypatch.setattr(hosted, 'head', lambda path: SimpleNamespace(pathname=path, size=1024**3 + 1), raising=False)
    archive = cloud.RemoteBlobArchive(f'uploads/{WORKSPACE}/{"6" * 32}.zip', WORKSPACE, tmp_path)
    with pytest.raises(WorkspaceError) as error:
        archive.open()
    assert error.value.status == 413 and hosted.reads == []
