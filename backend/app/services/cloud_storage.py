"""Private durable storage for hosted workspaces; /tmp is only an immutable cache.

Project records are the publication/authorization boundary. They are always read
from origin, while source bundles may be cached after their digest is verified.
No provider token or private Blob URL is returned to the browser.
"""
from __future__ import annotations

import hashlib
import atexit
import io
import json
import os
import re
import shutil
import tempfile
import threading
import zipfile
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from app.services.v1_errors import WorkspaceError

_PREFIX = 'grepo/v1/'
_ID = re.compile(r'^[a-f0-9]{32}$')
_WORKSPACE = re.compile(r'^[a-f0-9]{64}$')
_hydration_locks = [threading.Lock() for _ in range(32)]
_client_lock = threading.Lock()
_blob_client = None
MAX_BUNDLE_BYTES = 350 * 1024 * 1024
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_EXPANDED_BYTES = 350 * 1024 * 1024
MAX_BUNDLE_ENTRIES = 200_010


def enabled() -> bool:
    mode = os.environ.get('CODECANOPY_STORAGE', '').strip()
    if mode == 'vercel_blob':
        return True
    if os.environ.get('VERCEL'):
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Durable workspace storage is not configured.', 503)
    return False


def _sdk():
    """Keep HTTP connections warm without caching mutable ownership records."""
    global _blob_client
    try:
        from vercel.blob import BlobClient
    except ImportError:
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Durable workspace storage is unavailable.', 503) from None
    with _client_lock:
        if _blob_client is None:
            # Module-level SDK helpers create/close an HTTP client on every call.
            # The explicit client pools thread-safe HTTP connections across
            # requests served by the same hosted function instance.
            _blob_client = BlobClient()
            atexit.register(_blob_client.close)
        return _blob_client


def _id(value: str) -> str:
    if not _ID.fullmatch(value):
        raise WorkspaceError('NOT_FOUND', 'Workspace item not found.', 404)
    return value


def _workspace(value: str) -> str:
    if not _WORKSPACE.fullmatch(value):
        raise WorkspaceError('SESSION_REQUIRED', 'Open GREPO to start a workspace session.', 401)
    return value


def _item(workspace: str, kind: str, item_id: str) -> str:
    return f'{_PREFIX}workspaces/{_workspace(workspace)}/{kind}/{_id(item_id)}.json'


def _snapshot(snapshot_id: str, name: str) -> str:
    return f'{_PREFIX}snapshots/{_id(snapshot_id)}/{name}'


def _get(path: str) -> bytes | None:
    sdk = _sdk()
    from vercel.blob.errors import BlobNotFoundError
    try:
        result = sdk.get(path, access='private', use_cache=False, timeout=60)
        return result.content if result is not None else None
    except BlobNotFoundError:
        return None
    except Exception:
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Workspace storage could not be reached. Please retry.', 503) from None


def _put(path: str, data, *, overwrite: bool = True, content_type: str = 'application/json') -> None:
    try:
        _sdk().put(path, data, access='private', overwrite=overwrite,
                   add_random_suffix=False, content_type=content_type,
                   cache_control_max_age=60)
    except WorkspaceError:
        raise
    except Exception:
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Workspace storage could not save this change. Please retry.', 503) from None


def _delete(paths: list[str]) -> None:
    if not paths:
        return
    try:
        _sdk().delete(paths)
    except WorkspaceError:
        raise
    except Exception:
        raise WorkspaceError('STORAGE_UNAVAILABLE', 'Workspace storage could not complete deletion. Please retry.', 503) from None


def _list(prefix: str):
    cursor = None
    while True:
        try:
            page = _sdk().list_objects(prefix=prefix, cursor=cursor, limit=1000)
        except WorkspaceError:
            raise
        except Exception:
            raise WorkspaceError('STORAGE_UNAVAILABLE', 'Workspace storage could not be reached. Please retry.', 503) from None
        yield from page.blobs
        if not page.has_more:
            break
        if not page.cursor or page.cursor == cursor:
            raise WorkspaceError('STORAGE_UNAVAILABLE', 'Workspace storage returned an invalid page.', 503)
        cursor = page.cursor


def _read_json(path: str) -> dict | None:
    raw = _get(path)
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise WorkspaceError('STORAGE_INTEGRITY', 'Stored workspace metadata is invalid.', 503) from None


def _json_bytes(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=True, sort_keys=True).encode()


def load_project(workspace: str, project_id: str) -> dict | None:
    value = _read_json(_item(workspace, 'projects', project_id))
    if value is not None and (value.get('workspace_id') != workspace or value.get('id') != project_id):
        raise WorkspaceError('NOT_FOUND', 'Project not found.', 404)
    return value


def list_projects(workspace: str) -> list[dict]:
    prefix = f'{_PREFIX}workspaces/{_workspace(workspace)}/projects/'
    result = []
    project_ids = (item.pathname.removeprefix(prefix).removesuffix('.json') for item in _list(prefix))
    # Bound concurrency and queued work; keep every ownership check fresh.
    with ThreadPoolExecutor(max_workers=6) as executor:
        while batch := list(islice(project_ids, 24)):
            values = executor.map(lambda pid: load_project(workspace, pid),
                                  (pid for pid in batch if _ID.fullmatch(pid)))
            result.extend(value for value in values if value is not None)
    return result


def save_run(workspace: str, run_id: str, data: dict) -> None:
    _put(_item(workspace, 'runs', run_id), _json_bytes({**data, 'workspace_id': workspace}))


def load_run(workspace: str, run_id: str) -> dict | None:
    value = _read_json(_item(workspace, 'runs', run_id))
    if value is not None and (value.get('workspace_id') != workspace or value.get('id') != run_id):
        return None
    return value


def request_cancel(workspace: str, run_id: str) -> None:
    # Independent monotonic marker cannot be undone by an older progress writer.
    _put(_item(workspace, 'cancellations', run_id), b'{"cancel_requested":true}')


def cancellation_requested(workspace: str, run_id: str) -> bool:
    return _read_json(_item(workspace, 'cancellations', run_id)) is not None


def load_view(snapshot_id: str) -> dict | None:
    return _read_json(_snapshot(snapshot_id, 'view.json'))


def save_view(snapshot_id: str, data: dict) -> None:
    # The existing preferences API replaces the complete document. Preserve that
    # contract; all instances read the latest completed write without CDN cache.
    _put(_snapshot(snapshot_id, 'view.json'), _json_bytes(data))


def publish_snapshot(directory: Path, snapshot: dict, project: dict, workspace: str) -> None:
    """Upload immutable bytes first and publish the workspace pointer last."""
    sid = _id(snapshot['id'])
    project_path = _item(workspace, 'projects', project['id'])
    archive_path = _snapshot(sid, 'source.zip')
    descriptor_path = _snapshot(sid, 'snapshot.json')
    # Keep the compressed bundle in memory: hosted /tmp also contains the
    # retained source, and writing a second archive can exceed its disk budget.
    if sum(path.stat().st_size for path in directory.rglob('*') if path.is_file()) > MAX_EXPANDED_BYTES:
        raise WorkspaceError('SNAPSHOT_TOO_LARGE', 'Analyzed repository exceeds the hosted storage limit.', 413)
    with io.BytesIO() as bundle:
        with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for path in sorted(directory.rglob('*')):
                if path.is_symlink():
                    raise WorkspaceError('SOURCE_INTEGRITY', 'Source snapshot contains an invalid link.', 409)
                if path.is_file():
                    relative = path.relative_to(directory)
                    if relative.parts[0] in {'renders', 'view.json'}:
                        continue
                    archive.write(path, relative.as_posix())
        bundle.seek(0)
        digest = hashlib.file_digest(bundle, 'sha256').hexdigest()
        if bundle.seek(0, os.SEEK_END) > MAX_BUNDLE_BYTES:
            raise WorkspaceError('SNAPSHOT_TOO_LARGE', 'Analyzed repository exceeds the hosted storage limit.', 413)
        bundle.seek(0)
        descriptor = {'snapshot': snapshot, 'project': project, 'workspace_id': workspace,
                      'archive_sha256': digest}
        try:
            run_id = snapshot.get('analysis_run_id')
            if run_id and cancellation_requested(workspace, run_id):
                raise WorkspaceError('CANCELLED', 'Import cancelled.', 409)
            _put(archive_path, bundle, overwrite=False, content_type='application/zip')
            _put(descriptor_path, _json_bytes(descriptor), overwrite=False)
            if run_id and cancellation_requested(workspace, run_id):
                raise WorkspaceError('CANCELLED', 'Import cancelled.', 409)
            _put(project_path, _json_bytes({**project, 'workspace_id': workspace}), overwrite=False)
        except Exception:
            # The project pointer must not survive a failed publication.
            try:
                _delete([project_path, archive_path, descriptor_path])
            except WorkspaceError:
                pass
            raise


def _extract_bundle(raw: bytes, target: Path) -> None:
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError('bundle too large')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_BUNDLE_ENTRIES or sum(info.file_size for info in entries) > MAX_EXPANDED_BYTES:
            raise ValueError('bundle exceeds limits')
        seen = set()
        for info in entries:
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if (not info.filename or path.is_absolute() or '\\' in info.filename
                    or '..' in path.parts or mode & 0o170000 == 0o120000
                    or info.filename in seen):
                raise ValueError('unsafe bundle path')
            seen.add(info.filename)
            destination = target.joinpath(*path.parts)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, destination.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)


def hydrate_snapshot(snapshot_id: str, root: Path) -> None:
    """Reuse only a completely materialized immutable cache directory."""
    sid = _id(snapshot_id)
    directory = root / sid
    with _hydration_locks[int(sid[:2], 16) % len(_hydration_locks)]:
        if (directory / 'snapshot.json').is_file():
            return
        descriptor = _read_json(_snapshot(sid, 'snapshot.json'))
        if descriptor is None or descriptor.get('snapshot', {}).get('id') != sid:
            raise WorkspaceError('NOT_FOUND', 'Snapshot not found.', 404)
        snapshot = descriptor['snapshot']
        if datetime.fromisoformat(snapshot['expires_at']) <= datetime.now(timezone.utc):
            expire_snapshot(sid)
            raise WorkspaceError('EXPIRED', 'This snapshot has expired. Import the repository again.', 410)
        raw = _get(_snapshot(sid, 'source.zip'))
        if raw is None:
            raise WorkspaceError('NOT_FOUND', 'Snapshot not found.', 404)
        if hashlib.sha256(raw).hexdigest() != descriptor.get('archive_sha256'):
            raise WorkspaceError('SOURCE_INTEGRITY', 'Stored snapshot integrity check failed.', 409)
        staging = Path(tempfile.mkdtemp(prefix=f'.{sid}.hydrate-', dir=root))
        try:
            _extract_bundle(raw, staging)
            metadata = json.loads((staging / 'snapshot.json').read_text())
            if metadata != snapshot:
                raise ValueError('snapshot identity mismatch')
            staging.replace(directory)
            # Internal graph construction reads the already-authorized project
            # name from this local cache. Public access always rechecks Blob.
            project = {**descriptor['project'], 'workspace_id': descriptor['workspace_id']}
            temporary = root / f'.project_{project["id"]}.{sid}.tmp'
            temporary.write_bytes(_json_bytes(project))
            temporary.replace(root / f'project_{project["id"]}.json')
        except (ValueError, KeyError, OSError, zipfile.BadZipFile):
            raise WorkspaceError('SOURCE_INTEGRITY', 'Stored snapshot could not be restored safely.', 409) from None
        finally:
            shutil.rmtree(staging, ignore_errors=True)


def expire_snapshot(snapshot_id: str) -> None:
    _delete([_snapshot(snapshot_id, 'source.zip'), _snapshot(snapshot_id, 'view.json')])


def delete_project(workspace: str, project: dict) -> None:
    # Revoke access first. Subsequent authorized requests cannot use a warm cache.
    _delete([_item(workspace, 'projects', project['id'])])
    for sid in project['snapshot_ids']:
        _delete([_snapshot(sid, name) for name in ('source.zip', 'snapshot.json', 'view.json')])


def purge_expired() -> int:
    """Scheduled retention for durable sources, including abandoned publications."""
    now = datetime.now(timezone.utc)
    deleted = 0
    for item in _list(f'{_PREFIX}snapshots/'):
        if not item.pathname.endswith('/snapshot.json'):
            continue
        descriptor = _read_json(item.pathname)
        if descriptor is None:
            continue
        snapshot = descriptor['snapshot']
        expires = datetime.fromisoformat(snapshot['expires_at'])
        if expires <= now:
            sid = _id(snapshot['id'])
            _delete([_snapshot(sid, 'source.zip'), _snapshot(sid, 'view.json')])
            deleted += 1
            if expires + timedelta(days=1) <= now:
                _delete([item.pathname, _item(descriptor['workspace_id'], 'projects', snapshot['project_id'])])
    for item in _list(f'{_PREFIX}workspaces/'):
        if any(kind in item.pathname for kind in ('/runs/', '/cancellations/')) and item.uploaded_at + timedelta(days=2) <= now:
            _delete([item.pathname])
    for item in _list('uploads/'):
        if item.uploaded_at + timedelta(days=1) <= now:
            _delete([item.pathname])
    return deleted


class RemoteBlobArchive:
    """A verified private upload whose ZIP bytes are fetched by range, not staged."""
    def __init__(self, pathname: str, workspace: str, staging: Path):
        prefix = f'uploads/{_workspace(workspace)}/'
        if not pathname.startswith(prefix) or not re.fullmatch(r'[a-f0-9]{32}\.zip', pathname[len(prefix):]):
            raise WorkspaceError('NOT_FOUND', 'Uploaded archive not found in this workspace.', 404)
        self.pathname = pathname
        self.parent = staging

    def open(self, mode='rb'):
        if mode != 'rb':
            raise ValueError('Uploaded archives are read-only.')
        try:
            metadata = _sdk().head(self.pathname)
        except Exception:
            raise WorkspaceError('NOT_FOUND', 'Uploaded archive is unavailable. Upload it again.', 404) from None
        if metadata.pathname != self.pathname:
            raise WorkspaceError('SOURCE_INTEGRITY', 'Uploaded archive identity does not match.', 409)
        if metadata.size > MAX_UPLOAD_BYTES:
            raise WorkspaceError('UPLOAD_TOO_LARGE', 'The ZIP upload exceeds the 1 GiB limit.', 413)
        if metadata.size <= 0:
            raise WorkspaceError('INVALID_ARCHIVE', 'The uploaded ZIP is empty.', 400)
        return _BlobRangeReader(metadata.url, metadata.size)

    def discard(self):
        _delete([self.pathname])


class _BlobRangeReader(io.RawIOBase):
    """Bounded seekable reader for ZipFile's directory and selected members."""
    BLOCK = 1024 * 1024
    MAX_READ = 64 * 1024 * 1024

    def __init__(self, url: str, size: int):
        import httpx
        parsed = urlparse(url)
        if (parsed.scheme != 'https' or not parsed.hostname
                or not parsed.hostname.endswith('.private.blob.vercel-storage.com')
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise WorkspaceError('SOURCE_INTEGRITY', 'Uploaded archive location is invalid.', 409)
        token = os.environ.get('BLOB_READ_WRITE_TOKEN')
        if not token:
            raise WorkspaceError('STORAGE_UNAVAILABLE', 'Private upload storage is not configured.', 503)
        self.url, self.size, self.position = url, size, 0
        self.cache = OrderedDict()
        self.client = httpx.Client(headers={'Authorization': f'Bearer {token}'},
                                   timeout=30, follow_redirects=False)
        self.etag = None

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        position = offset + (0 if whence == io.SEEK_SET else self.position if whence == io.SEEK_CUR else self.size)
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END) or position < 0:
            raise ValueError('Invalid archive seek.')
        self.position = position
        return position

    def _block(self, index):
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        start = index * self.BLOCK
        end = min(start + self.BLOCK, self.size) - 1
        headers = {'Range': f'bytes={start}-{end}'}
        if self.etag:
            headers['If-Match'] = self.etag
        try:
            with self.client.stream('GET', self.url, headers=headers) as response:
                if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{self.size}':
                    raise WorkspaceError('STORAGE_UNAVAILABLE', 'Storage could not read the requested archive range.', 503)
                etag = response.headers.get('ETag')
                if self.etag and etag != self.etag:
                    raise WorkspaceError('SOURCE_INTEGRITY', 'Uploaded archive changed during import.', 409)
                self.etag = etag
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > end - start + 1:
                        raise WorkspaceError('SOURCE_INTEGRITY', 'Archive range exceeds its declared size.', 409)
                if len(content) != end - start + 1:
                    raise WorkspaceError('SOURCE_INTEGRITY', 'Archive range is incomplete.', 409)
        except WorkspaceError:
            raise
        except Exception:
            raise WorkspaceError('STORAGE_UNAVAILABLE', 'Uploaded archive could not be read. Please retry.', 503) from None
        self.cache[index] = bytes(content)
        while len(self.cache) > 4:
            self.cache.popitem(last=False)
        return self.cache[index]

    def read(self, size=-1):
        if self.closed:
            raise ValueError('Archive stream is closed.')
        size = max(0, min(self.size - self.position, self.size if size is None or size < 0 else size))
        if size > self.MAX_READ:
            raise WorkspaceError('INVALID_ARCHIVE', 'The ZIP directory exceeds the supported analysis size.', 413)
        chunks = []
        while size:
            index, offset = divmod(self.position, self.BLOCK)
            block = self._block(index)
            count = min(size, len(block) - offset)
            chunks.append(block[offset:offset + count])
            self.position += count
            size -= count
        return b''.join(chunks)

    def close(self):
        if not self.closed and hasattr(self, 'client'):
            self.client.close()
            self.cache.clear()
        super().close()
