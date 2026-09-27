"""Atomic immutable snapshot storage; source access never searches other projects."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models.codebase import File
from app.models.v1.snapshot import FilePage, FileRecord, Project, Snapshot, SnapshotSource, SourceKind
from app.models.v1.source import CapabilityReport, FileCapability, SourceSlice
from app.services.inventory_service import build_inventory, decode_text
from app.services.v1_errors import WorkspaceError

ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')
MAX_SOURCE_BYTES = 256 * 1024


class SnapshotNotFoundError(WorkspaceError):
    def __init__(self, message='Snapshot not found.'):
        super().__init__('NOT_FOUND', message, 404)


def _v1_root() -> Path:
    root = Path(os.environ.get('CODECANOPY_SNAPSHOTS_DIR', str(Path(tempfile.gettempdir()) / 'codecanopy' / 'snapshots'))).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _retry_readonly_removal(function, path, error_info) -> None:
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        function(path)
    except OSError:
        raise error_info[1]


def remove_tree(path: Path, *, ignore_errors: bool = False) -> None:
    try:
        shutil.rmtree(path, onerror=_retry_readonly_removal)
    except OSError:
        if not ignore_errors:
            raise


def _read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, data) -> None:
    temporary = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True), encoding='utf-8')
    temporary.replace(path)


def checked_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise SnapshotNotFoundError()
    return value


def get_project(project_id: str, workspace_id: str | None = None) -> Project:
    path = _v1_root() / f'project_{checked_id(project_id)}.json'
    try:
        data = _read_json(path)
    except (OSError, ValueError):
        raise SnapshotNotFoundError('Project not found.') from None
    if workspace_id is not None and data.get('workspace_id') != workspace_id:
        raise SnapshotNotFoundError('Project not found.')
    return Project.model_validate(data)


def list_projects(workspace_id: str) -> list[Project]:
    projects = []
    for path in _v1_root().glob('project_*.json'):
        try:
            data = _read_json(path)
            if data.get('workspace_id') == workspace_id:
                projects.append(Project.model_validate(data))
        except (OSError, ValueError):
            continue
    return sorted(projects, key=lambda p: p.created_at, reverse=True)


def get_snapshot(snapshot_id: str) -> Snapshot:
    path = _v1_root() / checked_id(snapshot_id) / 'snapshot.json'
    try:
        snapshot = Snapshot.model_validate(_read_json(path))
    except (OSError, ValueError):
        raise SnapshotNotFoundError() from None
    if snapshot.expires_at and snapshot.expires_at <= datetime.now(timezone.utc):
        raise WorkspaceError('EXPIRED', 'This snapshot has expired. Import the repository again.', 410)
    return snapshot


def authorized_snapshot(project_id: str, snapshot_id: str, workspace_id: str) -> Snapshot:
    project = get_project(project_id, workspace_id)
    if snapshot_id not in project.snapshot_ids:
        raise SnapshotNotFoundError()
    snap = get_snapshot(snapshot_id)
    if snap.project_id != project_id:
        raise SnapshotNotFoundError()
    return snap


def create_snapshot_from_project(project_id: str, project_dir: Path, archive_digest: str,
                                 project_name: str, *, workspace_id: str = '', run_id: str | None = None,
                                 source: SnapshotSource | None = None, check_cancel=lambda: None):
    checked_id(project_id)
    snapshot_id = uuid.uuid4().hex
    root = _v1_root()
    staging = root / f'.{snapshot_id}.staging'
    staging.mkdir(mode=0o700)
    try:
        records, parsed, diagnostics = build_inventory(snapshot_id, project_dir, staging / 'files', check_cancel)
        manifest = [{'path': r.path, 'hash': r.content_hash, 'excluded': r.excluded} for r in records]
        now = datetime.now(timezone.utc)
        snapshot = Snapshot(
            id=snapshot_id, project_id=project_id,
            source=source or SnapshotSource(kind=SourceKind.ZIP, archive_digest=archive_digest, display_ref='local upload'),
            manifest_hash=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            created_at=now, expires_at=now + timedelta(hours=24), analysis_run_id=run_id,
        )
        _write_json(staging / 'snapshot.json', snapshot.model_dump(mode='json'))
        _write_json(staging / 'inventory.json', [r.model_dump(mode='json') for r in records])
        _write_json(staging / 'syntax.json', parsed)
        _write_json(staging / 'diagnostics.json', [d.model_dump(mode='json') for d in diagnostics])
        check_cancel()
        staging.replace(root / snapshot_id)
        project = Project(id=project_id, name=project_name, created_at=now, snapshot_ids=[snapshot_id])
        _write_json(root / f'project_{project_id}.json', {**project.model_dump(mode='json'), 'workspace_id': workspace_id})
        return snapshot, records
    except Exception:
        # The project metadata is the publication boundary. A failed publish must
        # not leave a detached source directory after staging has been renamed.
        remove_tree(root / snapshot_id, ignore_errors=True)
        raise
    finally:
        if staging.exists():
            remove_tree(staging)


def create_snapshot_from_github(owner: str, repo: str, resolved_commit: str, display_ref: str,
                                project_name: str, files_dir: Path, *, project_id: str | None = None,
                                workspace_id: str = '', run_id: str | None = None, check_cancel=lambda: None):
    project_id = project_id or uuid.uuid4().hex
    snapshot, records = create_snapshot_from_project(
        project_id, files_dir, '', project_name, workspace_id=workspace_id, run_id=run_id,
        source=SnapshotSource(kind=SourceKind.GITHUB, owner=owner, repo=repo, resolved_commit=resolved_commit, display_ref=display_ref),
        check_cancel=check_cancel,
    )
    return project_id, snapshot, records


def get_inventory(snapshot_id: str, cursor: str | None = None, limit: int = 500) -> FilePage:
    get_snapshot(snapshot_id)
    if cursor is not None and (not cursor.isascii() or not cursor.isdigit()):
        raise WorkspaceError('INVALID_CURSOR', 'The inventory cursor is invalid.', 422)
    start = int(cursor or 0)
    records = [FileRecord.model_validate(r) for r in _read_json(_v1_root() / snapshot_id / 'inventory.json')]
    if start > len(records):
        raise WorkspaceError('INVALID_CURSOR', 'The inventory cursor is out of range.', 422)
    next_cursor = str(start + limit) if start + limit < len(records) else None
    return FilePage(snapshot_id=snapshot_id, files=records[start:start + limit], total=len(records), cursor=next_cursor, truncated=next_cursor is not None)


def get_file_record(snapshot_id: str, file_id: str) -> FileRecord:
    checked_id(file_id)
    for record in get_inventory(snapshot_id, limit=10000).files:
        if record.id == file_id:
            return record
    raise SnapshotNotFoundError('File not found in this snapshot.')


def get_syntax_records(snapshot_id: str) -> dict[str, File]:
    get_snapshot(snapshot_id)
    parsed = _read_json(_v1_root() / snapshot_id / 'syntax.json')
    return {file_id: File.model_validate(record) for file_id, record in parsed.items()}


def get_project_snapshots(project_id: str, workspace_id: str | None = None) -> list[Snapshot]:
    project = get_project(project_id, workspace_id)
    return [get_snapshot(sid) for sid in project.snapshot_ids]


def build_capability_report(snapshot_id: str) -> CapabilityReport:
    records = get_inventory(snapshot_id, limit=10000).files
    parsed = _read_json(_v1_root() / snapshot_id / 'syntax.json')
    diagnostics = _read_json(_v1_root() / snapshot_id / 'diagnostics.json')
    files = []
    for rec in records:
        syntax = rec.id in parsed
        parser_name = parsed[rec.id].get('parser') if syntax else None
        level = 'excluded' if rec.excluded else 'binary' if not rec.is_text else 'full' if syntax else 'text_only'
        limitations = [d['message'] for d in diagnostics if d['file_path'] == rec.path]
        if rec.excluded:
            limitations.append(rec.exclusion_reason)
        elif rec.is_text and not syntax:
            limitations.append('This file has no successful configured syntax extraction; function findings do not include it.')
        files.append(FileCapability(file_id=rec.id, path=rec.path, language=rec.language, level=level,
                                    syntax_extraction=syntax, reference_resolution=False, summary_eligible=False,
                                    parser_name=parser_name, limitations=limitations))
    return CapabilityReport(snapshot_id=snapshot_id, files=files,
        parsed_count=sum(f.syntax_extraction for f in files), text_only_count=sum(f.level == 'text_only' for f in files),
        binary_count=sum(f.level == 'binary' for f in files), excluded_count=sum(f.level == 'excluded' for f in files),
        limitations=[
            'Syntax extraction is bounded to 1 MiB per file.',
            'Function findings support Python, JavaScript, TypeScript/TSX, Go, Rust, Java, Kotlin, C/C++, C#, Ruby, PHP, Bash and SQL. Other languages remain text-only.',
            'Call references are name-based and cannot resolve imports, dynamic dispatch, reflection or framework registration.',
            'AI semantic duplicate scoring runs only when a backend provider is configured.',
        ])


def read_source_lines(snapshot_id: str, file_id: str, line_start: int = 1, line_end: int | None = None, max_lines: int = 500) -> SourceSlice:
    rec = get_file_record(snapshot_id, file_id)
    if rec.excluded:
        raise WorkspaceError('SOURCE_EXCLUDED', rec.exclusion_reason or 'Source excluded.', 403)
    if not rec.is_text:
        raise WorkspaceError('SOURCE_NOT_TEXT', 'Binary or unsupported encoding; source preview is unavailable.', 415)
    root = _v1_root() / snapshot_id / 'files'
    file = root / rec.path
    if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
        raise WorkspaceError('SOURCE_INTEGRITY', 'Source integrity check failed.', 409)
    try:
        data = file.read_bytes()
    except OSError:
        raise WorkspaceError('SOURCE_EXPIRED', 'Source is no longer available. Import again.', 410) from None
    if hashlib.sha256(data).hexdigest() != rec.content_hash:
        raise WorkspaceError('SOURCE_INTEGRITY', 'Source content does not match this immutable snapshot.', 409)
    text, _ = decode_text(data, rec.language)
    if text is None:
        raise WorkspaceError('SOURCE_NOT_TEXT', 'Source encoding is unsupported.', 415)
    lines = text.splitlines()
    if line_start < 1 or max_lines < 1 or max_lines > 2000 or (line_end is not None and line_end < line_start) or line_start > max(1, len(lines)):
        raise WorkspaceError('INVALID_RANGE', 'Source line range is invalid or out of bounds.', 422)
    end = min(line_end or len(lines), len(lines), line_start + max_lines - 1)
    selected, size = [], 0
    for line in lines[line_start - 1:end]:
        size += len(line.encode('utf-8')) + 1
        if size > MAX_SOURCE_BYTES:
            if not selected:
                raise WorkspaceError('SOURCE_LINE_TOO_LARGE', 'This line exceeds the 256 KiB preview limit.', 413)
            break
        selected.append(line)
    actual_end = line_start + len(selected) - 1
    return SourceSlice(file_id=file_id, snapshot_id=snapshot_id, path=rec.path, line_start=line_start,
                       line_end=actual_end, total_lines=len(lines), content='\n'.join(selected),
                       truncated=actual_end < len(lines), content_hash=rec.content_hash)


def delete_project(project_id: str, workspace_id: str) -> None:
    project = get_project(project_id, workspace_id)
    (_v1_root() / f'project_{project_id}.json').unlink()
    for snapshot_id in project.snapshot_ids:
        remove_tree(_v1_root() / checked_id(snapshot_id), ignore_errors=True)
