import io
import zipfile

import pytest

from app.services import project_archive as archives
from app.services import syntax_process
from app.services.syntax_process import SyntaxProcess
from app.services.snapshot_service import create_snapshot_from_project, get_file_record, get_inventory, read_source_lines


def archive_with(names):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for name in names:
            archive.writestr(name, 'hello\n')
    return zipfile.ZipFile(data)


def test_large_archive_filters_dependencies_before_project_file_limit(monkeypatch):
    monkeypatch.setattr(archives, 'MAX_PROJECT_FILES', 1)
    with archive_with([f'repo/node_modules/pkg/{i}.js' for i in range(10_001)] + ['repo/main.py']) as archive:
        entries = archives._validated_entries(archive)
    assert [e.relative_path.as_posix() for e in entries] == ['repo/main.py']


def test_large_source_archive_and_bounded_limits(monkeypatch):
    with archive_with([f'src/{i}.txt' for i in range(10_001)]) as archive:
        assert len(archives._validated_entries(archive)) == 10_001
    monkeypatch.setattr(archives, 'MAX_PROJECT_FILES', 2)
    with archive_with(['a.txt', 'b.txt', 'c.txt']) as archive:
        with pytest.raises(archives.ProjectUploadError, match='after dependency'):
            archives._validated_entries(archive)
    monkeypatch.setattr(archives, 'MAX_ARCHIVE_ENTRIES', 2)
    with archive_with(['node_modules/a', 'node_modules/b', 'src/c']) as archive:
        with pytest.raises(archives.ProjectUploadError, match='at most 2 entries'):
            archives._validated_entries(archive)


def test_ignored_paths_still_reject_traversal_and_extraction_can_cancel(tmp_path):
    with archive_with(['node_modules/../../escape.txt']) as archive:
        with pytest.raises(archives.ProjectUploadError):
            archives._validated_entries(archive)
    with archive_with(['main.txt']) as archive:
        def cancel():
            raise RuntimeError('cancelled')
        with pytest.raises(RuntimeError, match='cancelled'):
            archives._extract_entries(archive, archives._validated_entries(archive), tmp_path / 'files', cancel)
    assert not (tmp_path / 'files/main.txt').exists()


def payload(path='a.py', text='def add(a, b):\n    return a + b\n', language='python'):
    return dict(path=path, text=text, size=len(text.encode()), language=language)


def test_reusable_parser_preserves_file_identity_and_recovers_after_failure(monkeypatch):
    monkeypatch.setattr(syntax_process, 'MAX_REQUESTS', 2)
    with SyntaxProcess() as parser:
        first = parser.parse(payload()); process = parser.process
        second = parser.parse(payload('b.ts', 'export function hello() { return 2; }', 'typescript'))
        assert parser.process is process
        assert first['functions'][0]['file'] == 'a.py'
        assert second['functions'][0]['file'] == 'b.ts'
        assert second['functions'][0]['name'] == 'hello'
        parser.parse(payload('c.py'))
        assert parser.process is not process and process.poll() is not None
        with pytest.raises(ValueError):
            parser.parse(payload('bad.py', 'def !!!'))
        assert parser.parse(payload('good.py'))['path'] == 'good.py'
    assert parser.process is None


def test_parser_timeout_and_cancellation_kill_child(monkeypatch):
    monkeypatch.setattr(syntax_process, 'PARSE_TIMEOUT', 0)
    with SyntaxProcess() as parser:
        with pytest.raises(syntax_process.subprocess.TimeoutExpired):
            parser.parse(payload())
        assert parser.process is None
    monkeypatch.setattr(syntax_process, 'PARSE_TIMEOUT', 10)
    def cancel():
        raise RuntimeError('cancelled')
    with SyntaxProcess() as parser:
        with pytest.raises(RuntimeError, match='cancelled'):
            parser.parse(payload(), cancel)
        assert parser.process is None


def test_source_past_old_limit_is_accessible_and_cached_source_still_checked(tmp_path, monkeypatch):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    source = tmp_path / 'source'; source.mkdir()
    for i in range(10_001):
        (source / f'{i:05}.txt').write_text('hello\n')
    progress = []
    snap, records = create_snapshot_from_project('a' * 32, source, 'test', 'Large fixture', report_progress=lambda done, total: progress.append((done, total)))
    assert get_inventory(snap.id, limit=None).total == 10_001
    last = records[-1]
    assert get_file_record(snap.id, last.id).path == '10000.txt'
    assert read_source_lines(snap.id, last.id).content == 'hello'
    assert progress[0] == (0, 10_001) and progress[-1] == (10_001, 10_001)
    target = tmp_path / 'snapshots' / snap.id / 'files' / last.path
    target.chmod(0o644); target.write_text('tampered')
    from app.services.v1_errors import WorkspaceError
    with pytest.raises(WorkspaceError, match='immutable snapshot'):
        read_source_lines(snap.id, last.id)


def test_v1_can_skip_symlinks_without_extracting_or_following_targets(tmp_path):
    import stat
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        link = zipfile.ZipInfo('repo/link')
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, '../../outside-secret')
        archive.writestr('repo/main.txt', 'safe')
    skipped = []
    with zipfile.ZipFile(data) as archive:
        entries = archives._validated_entries(archive, skip_symlinks=True, on_skip=skipped.append)
        archives._extract_entries(archive, entries, tmp_path / 'files')
    assert skipped == ['repo/link']
    assert (tmp_path / 'files/repo/main.txt').read_text() == 'safe'
    assert not (tmp_path / 'files/repo/link').exists()
