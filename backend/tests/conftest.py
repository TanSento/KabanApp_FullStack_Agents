import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import create_app
from app.auth import clear_sessions


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(db_path):
    """Client with a fresh temp database and no static dir."""
    clear_sessions()
    app = create_app(static_dir=None, db_path=db_path)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_client(client):
    """Client with a valid auth token already set up."""
    resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
