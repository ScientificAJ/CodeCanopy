"""GitHub download budget is independent of browser ZIP uploads."""
import io
import zipfile

import pytest

from app.services import github_import as github

SHA = 'a' * 40


def test_github_import_above_former_50_mib_limit(monkeypatch, tmp_path):
    fixture = tmp_path / 'large-repository.zip'
    with zipfile.ZipFile(fixture, 'w', compression=zipfile.ZIP_STORED) as archive:
        with archive.open('repo/node_modules/package/payload.bin', 'w') as member:
            for _ in range(51):
                member.write(b'x' * (1024 * 1024))
        archive.writestr('repo/main.py', 'print("complete source")\n')
    assert fixture.stat().st_size > 50 * 1024 * 1024
    assert fixture.stat().st_size < github.MAX_GITHUB_ARCHIVE_BYTES
    monkeypatch.setattr(github, '_open', lambda url: fixture.open('rb'))
    monkeypatch.setattr(github, 'resolve_ref_to_commit', lambda *args: (SHA, 'main'))
    monkeypatch.setattr(github.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path / 'staging'))
    (tmp_path / 'staging').mkdir()
    _, _, commit, _, _, files, _ = github.import_github_repository('https://github.com/a/repo')
    assert commit == SHA
    assert (files / 'main.py').read_text() == 'print("complete source")\n'
    assert not (files / 'node_modules').exists()


@pytest.mark.parametrize('length,accepted', [(15, True), (16, True), (17, False)])
def test_download_stream_limit_and_cleanup(monkeypatch, tmp_path, length, accepted):
    monkeypatch.setattr(github, 'MAX_GITHUB_ARCHIVE_BYTES', 16)
    monkeypatch.setattr(github, 'DOWNLOAD_CHUNK_BYTES', 4)
    monkeypatch.setattr(github, '_open', lambda url: io.BytesIO(b'x' * length))
    if accepted:
        result = github.download_archive('a', 'repo', SHA, tmp_path)
        assert result.read_bytes() == b'x' * length
    else:
        with pytest.raises(github.GitHubImportTooLargeError):
            github.download_archive('a', 'repo', SHA, tmp_path)
        assert not (tmp_path / 'github.zip').exists()


def test_cancelled_download_removes_partial_file(monkeypatch, tmp_path):
    monkeypatch.setattr(github, 'DOWNLOAD_CHUNK_BYTES', 4)
    monkeypatch.setattr(github, '_open', lambda url: io.BytesIO(b'x' * 16))
    checks = []
    def cancel():
        if checks:
            raise RuntimeError('cancelled')
        checks.append(True)
    with pytest.raises(RuntimeError, match='cancelled'):
        github.download_archive('a', 'repo', SHA, tmp_path, cancel)
    assert not (tmp_path / 'github.zip').exists()


def test_existing_download_is_not_deleted(monkeypatch, tmp_path):
    archive = tmp_path / 'github.zip'
    archive.write_bytes(b'existing')
    monkeypatch.setattr(github, '_open', lambda url: io.BytesIO(b'new'))
    with pytest.raises(FileExistsError):
        github.download_archive('a', 'repo', SHA, tmp_path)
    assert archive.read_bytes() == b'existing'
