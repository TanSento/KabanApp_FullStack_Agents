from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_index_when_static_dir_exists(tmp_path):
    """When static/ exists with an index.html, GET / serves it."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>Kanban Studio</body></html>")
    (static_dir / "_next").mkdir()

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text


def test_health_still_works_with_static_dir(tmp_path):
    """API routes work even when static file serving is active."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html></html>")
    (static_dir / "_next").mkdir()

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_file_served_directly(tmp_path):
    """Specific static files are served by their exact path."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html></html>")
    (static_dir / "_next").mkdir()
    (static_dir / "favicon.ico").write_bytes(b"fake-icon")

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.content == b"fake-icon"


def test_spa_fallback_to_index(tmp_path):
    """Unknown paths fall back to index.html for SPA routing."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>SPA</body></html>")
    (static_dir / "_next").mkdir()

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/some/unknown/path")
    assert response.status_code == 200
    assert "SPA" in response.text
