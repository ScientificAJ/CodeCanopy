from io import BytesIO
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_expected_payload() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_upload_endpoint_extracts_zip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CODECANOPY_PROJECTS_DIR", str(tmp_path))
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as project_zip:
        project_zip.writestr("demo/main.py", "print('data only')\n")
        project_zip.writestr("demo/src/view.ts", "export const ready = true\n")
        project_zip.writestr("demo/package.json", "{}")
        project_zip.writestr("demo/.git/config", "ignored")

    response = client.post(
        "/api/projects",
        files={"file": ("demo.zip", archive.getvalue(), "application/zip")},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "uploaded"
    assert result["name"] == "demo"
    assert result["file_count"] == 3
    assert (tmp_path / result["project_id"] / "demo" / "main.py").read_text() == "print('data only')\n"
    assert not (tmp_path / result["project_id"] / "demo" / ".git").exists()

    project_response = client.get(f"/api/projects/{result['project_id']}")
    files_response = client.get(f"/api/projects/{result['project_id']}/files")

    assert project_response.status_code == 200
    assert project_response.json()["name"] == "demo"
    inventory = {item["path"]: item for item in project_response.json()["files"]}
    assert inventory["demo/main.py"]["language"] == "python"
    assert inventory["demo/src/view.ts"]["language"] == "typescript"
    assert inventory["demo/package.json"]["language"] == "json"
    assert files_response.status_code == 200
    assert files_response.json() == project_response.json()["files"]


def test_project_analyze_returns_structured_python_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CODECANOPY_PROJECTS_DIR", str(tmp_path))
    archive = BytesIO()
    auth_source = "import database\n\n\ndef login():\n    return database.connect()\n"
    with zipfile.ZipFile(archive, "w") as project_zip:
        project_zip.writestr("src/auth.py", auth_source)
        project_zip.writestr("src/readme.txt", "not source")

    upload_response = client.post(
        "/api/projects",
        files={"file": ("project.zip", archive.getvalue(), "application/zip")},
    )
    project_id = upload_response.json()["project_id"]

    response = client.post(f"/api/projects/{project_id}/analyze")

    assert response.status_code == 200
    assert response.json() == [
        {
            "path": "src/auth.py",
            "name": "auth.py",
            "language": "python",
            "size": len(auth_source.encode("utf-8")),
            "functions": [{"name": "login", "file": "src/auth.py", "line_start": 4, "line_end": 5}],
            "classes": [],
            "imports": ["database"],
            "call_sites": [{"callee_name": "connect", "file": "src/auth.py", "line_start": 5, "line_end": 5}],
        }
    ]


def test_project_analyze_returns_not_found_for_unknown_project() -> None:
    response = client.post("/api/projects/00000000000000000000000000000000/analyze")

    assert response.status_code == 404
