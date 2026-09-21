from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "ai", "password": "No_comment_123"})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "ai"
    assert "lac_session" in response.cookies


def test_login_failure(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "ai", "password": "wrong"})
    assert response.status_code == 401


def test_me_requires_auth(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_password_change(admin_client: TestClient):
    response = admin_client.put(
        "/api/auth/password",
        json={"current_password": "No_comment_123", "new_password": "NewPass_456"},
    )
    assert response.status_code == 200
    admin_client.post("/api/auth/logout")
    failed = admin_client.post("/api/auth/login", json={"username": "ai", "password": "No_comment_123"})
    assert failed.status_code == 401
    ok = admin_client.post("/api/auth/login", json={"username": "ai", "password": "NewPass_456"})
    assert ok.status_code == 200
