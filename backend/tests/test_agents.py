from fastapi.testclient import TestClient


def test_agent_crud(admin_client: TestClient):
    created = admin_client.post(
        "/api/agents",
        json={"name": "HR Agent", "description": "HR dokumentumok", "system_prompt": "Légy tömör."},
    )
    assert created.status_code == 201
    agent_id = created.json()["id"]
    listed = admin_client.get("/api/agents")
    assert listed.status_code == 200
    assert any(item["id"] == agent_id for item in listed.json())
    fetched = admin_client.get(f"/api/agents/{agent_id}")
    assert fetched.json()["name"] == "HR Agent"
    updated = admin_client.put(f"/api/agents/{agent_id}", json={"status": "inactive", "name": "HR"})
    assert updated.json()["status"] == "inactive"
    assert updated.json()["name"] == "HR"
    deleted = admin_client.delete(f"/api/agents/{agent_id}")
    assert deleted.status_code == 202


def test_agent_not_found(admin_client: TestClient):
    response = admin_client.get("/api/agents/does-not-exist")
    assert response.status_code == 404
