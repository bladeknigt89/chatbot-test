from fastapi.testclient import TestClient


def test_audit_logging(admin_client: TestClient):
    admin_client.post("/api/agents", json={"name": "Audit Agent"})
    logs = admin_client.get("/api/logs", params={"action": "AGENT_CREATED"})
    assert logs.status_code == 200
    assert logs.json()
    assert logs.json()[0]["action"] == "AGENT_CREATED"
    assert logs.json()[0]["resource_type"] == "agent"


def test_dashboard(admin_client: TestClient):
    response = admin_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "agent_count" in body
    assert "document_count" in body
    assert "processing_document_count" in body
    assert "api_key_count" in body
    assert "chat_requests_today" in body
    assert "errors_today" in body


def test_settings_chat_history(admin_client: TestClient):
    current = admin_client.get("/api/settings")
    assert current.status_code == 200
    updated = admin_client.put("/api/settings", json={"chat_history_enabled": False})
    assert updated.json()["chat_history_enabled"] is False
