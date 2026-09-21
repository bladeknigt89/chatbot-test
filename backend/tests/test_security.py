from fastapi.testclient import TestClient

from tests.conftest import make_pdf


def test_invalid_file_type(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "Sec"}).json()
    response = admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("malware.exe", b"MZ\x90\x00not-a-document", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_pdf_extension_with_wrong_content(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "Sec2"}).json()
    response = admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("fake.pdf", b"this is not a pdf", "application/pdf")},
    )
    assert response.status_code == 400


def test_oversized_file(admin_client: TestClient, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_file_size", 100)
    agent = admin_client.post("/api/agents", json={"name": "Sec3"}).json()
    response = admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("big.pdf", make_pdf("hello world " * 50), "application/pdf")},
    )
    assert response.status_code == 400


def test_path_traversal_filename(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "Sec4"}).json()
    response = admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("../../secret.pdf", make_pdf("hello"), "application/pdf")},
    )
    assert response.status_code == 202
    stored = response.json()["original_filename"]
    assert ".." not in stored
    assert "/" not in stored
    assert "\\" not in stored


def test_unauthorized_agent_access(client: TestClient):
    response = client.get("/api/agents")
    assert response.status_code == 401
    response = client.get("/api/logs")
    assert response.status_code == 401
