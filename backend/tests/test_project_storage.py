import asyncio
from io import BytesIO
import stat
import zipfile

import pytest
from fastapi import UploadFile

from app.services import project_archive
from app.services.project_archive import ProjectUploadError, ProjectUploadTooLargeError
from app.services.project_storage import store_project_archive


def make_archive(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def make_upload(content: bytes) -> UploadFile:
    return UploadFile(filename="project.zip", file=BytesIO(content))


def test_upload_skips_unnecessary_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))
    archive = make_archive(
        {
            "src/main.py": b"def main(): pass\n",
            ".git/config": b"git data",
            "node_modules/package/index.js": b"dependency",
            "__pycache__/module.pyc": b"cache",
            ".venv/pyvenv.cfg": b"environment",
            "dist/bundle.js": b"build output",
            "build/result.txt": b"build output",
            "build": b"a file, not a directory",
        }
    )

    result = asyncio.run(store_project_archive(make_upload(archive)))

    destination = tmp_path / result.project_id
    assert result.file_count == 2
    assert (destination / "src" / "main.py").is_file()
    assert (destination / "build").read_bytes() == b"a file, not a directory"
    assert sorted(path.name for path in destination.iterdir()) == ["build", "src"]


@pytest.mark.parametrize(
    "unsafe_path",
    ["../escape.txt", "C:/escape.txt", r"..\escape.txt", "src/invalid?.py"],
)
def test_upload_rejects_path_traversal(tmp_path, monkeypatch, unsafe_path: str) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))

    with pytest.raises(ProjectUploadError, match="path"):
        asyncio.run(store_project_archive(make_upload(make_archive({unsafe_path: b"blocked"}))))

    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_symbolic_links(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))
    archive_bytes = BytesIO()
    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr(link, "target.txt")

    with pytest.raises(ProjectUploadError, match="Symbolic links"):
        asyncio.run(store_project_archive(make_upload(archive_bytes.getvalue())))

    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_non_zip_content(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))

    with pytest.raises(ProjectUploadError, match="valid supported ZIP"):
        asyncio.run(store_project_archive(make_upload(b"not a ZIP archive")))

    assert list(tmp_path.iterdir()) == []


def test_upload_enforces_compressed_size_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(project_archive, "MAX_UPLOAD_BYTES", 10)

    with pytest.raises(ProjectUploadTooLargeError):
        asyncio.run(store_project_archive(make_upload(make_archive({"large.txt": b"too much data"}))))

    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_file_directory_collisions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GREPO_PROJECTS_DIR", str(tmp_path))

    with pytest.raises(ProjectUploadError, match="conflicts with a directory"):
        asyncio.run(store_project_archive(make_upload(make_archive({"src": b"file", "src/main.py": b"code"}))))

    assert list(tmp_path.iterdir()) == []