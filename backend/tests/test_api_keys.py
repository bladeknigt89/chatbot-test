from fastapi.testclient import TestClient


def test_api_key_lifecycle(admin_client: TestClient):
    created = admin_client.post("/api/keys", json={"name": "integracio"})
    assert created.status_code == 201
    raw = created.json()["key"]
    assert raw.startswith("lac_")
    key_id = created.json()["id"]
    listed = admin_client.get("/api/keys")
    assert listed.status_code == 200
    assert "key" not in listed.json()[0]
    headers = {"Authorization": f"Bearer {raw}"}
    agent = admin_client.post("/api/agents", json={"name": "API Agent"}, headers=headers)
    assert agent.status_code == 201
    revoked = admin_client.post(f"/api/keys/{key_id}/revoke")
    assert revoked.json()["status"] == "revoked"
    denied = admin_client.post("/api/agents", json={"name": "X"}, headers=headers)
    assert denied.status_code == 403
    deleted = admin_client.delete(f"/api/keys/{key_id}")
    assert deleted.status_code == 204


def test_invalid_api_key(client: TestClient):
    response = client.get("/api/agents", headers={"Authorization": "Bearer lac_invalid_key_value_000"})
    assert response.status_code == 401
