from app.auth import clear_sessions


def test_login_success(client):
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["username"] == "user"


def test_login_wrong_credentials(client):
    response = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
    assert response.status_code == 401


def test_me_with_valid_token(client):
    login_resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    token = login_resp.json()["token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "user"


def test_me_without_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_logout_invalidates_token(client):
    login_resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    token = login_resp.json()["token"]

    # Logout
    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # Token should now be invalid
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_health_does_not_require_auth(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
