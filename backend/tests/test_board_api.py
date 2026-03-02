"""Tests for board API endpoints."""


def test_get_board_returns_seeded_data(auth_client):
    resp = auth_client.get("/api/board")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 5
    assert data["columns"][0]["title"] == "Backlog"
    assert len(data["cards"]) == 8


def test_get_board_requires_auth(client):
    resp = client.get("/api/board")
    assert resp.status_code == 422 or resp.status_code == 401


def test_rename_column(auth_client):
    resp = auth_client.put("/api/board/columns/col-backlog", json={"title": "To Do"})
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert board["columns"][0]["title"] == "To Do"


def test_rename_column_not_found(auth_client):
    resp = auth_client.put("/api/board/columns/col-fake", json={"title": "Nope"})
    assert resp.status_code == 404


def test_create_card(auth_client):
    resp = auth_client.post("/api/board/cards", json={
        "column_id": "col-backlog",
        "id": "card-new-1",
        "title": "New card",
        "details": "Some details",
    })
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert "card-new-1" in board["cards"]
    assert board["cards"]["card-new-1"]["title"] == "New card"
    assert "card-new-1" in board["columns"][0]["cardIds"]


def test_create_card_in_nonexistent_column(auth_client):
    resp = auth_client.post("/api/board/cards", json={
        "column_id": "col-fake",
        "id": "card-fail",
        "title": "Nope",
    })
    assert resp.status_code == 404


def test_update_card(auth_client):
    resp = auth_client.put("/api/board/cards/card-1", json={
        "title": "Updated title",
        "details": "Updated details",
    })
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert board["cards"]["card-1"]["title"] == "Updated title"
    assert board["cards"]["card-1"]["details"] == "Updated details"


def test_update_card_not_found(auth_client):
    resp = auth_client.put("/api/board/cards/card-fake", json={
        "title": "Nope",
        "details": "Nope",
    })
    assert resp.status_code == 404


def test_delete_card(auth_client):
    resp = auth_client.delete("/api/board/cards/card-1")
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert "card-1" not in board["cards"]
    assert "card-1" not in board["columns"][0]["cardIds"]


def test_delete_card_not_found(auth_client):
    resp = auth_client.delete("/api/board/cards/card-fake")
    assert resp.status_code == 404


def test_move_card_to_different_column(auth_client):
    resp = auth_client.put("/api/board/cards/card-1/move", json={
        "column_id": "col-done",
        "position": 0,
    })
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert "card-1" not in board["columns"][0]["cardIds"]  # removed from Backlog
    assert "card-1" in board["columns"][4]["cardIds"]  # added to Done


def test_move_card_not_found(auth_client):
    resp = auth_client.put("/api/board/cards/card-fake/move", json={
        "column_id": "col-done",
        "position": 0,
    })
    assert resp.status_code == 404


def test_bulk_update(auth_client):
    new_board = {
        "columns": [
            {"id": "col-a", "title": "Alpha", "cardIds": ["card-x"]},
            {"id": "col-b", "title": "Beta", "cardIds": []},
        ],
        "cards": {
            "card-x": {"id": "card-x", "title": "Only card", "details": ""},
        },
    }
    resp = auth_client.put("/api/board", json=new_board)
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert len(board["columns"]) == 2
    assert board["columns"][0]["title"] == "Alpha"
    assert len(board["cards"]) == 1


def test_db_auto_created(tmp_path):
    """The DB file is created automatically on first request."""
    from app.main import create_app
    from app.auth import clear_sessions
    from fastapi.testclient import TestClient

    db_file = tmp_path / "auto.db"
    assert not db_file.exists()

    clear_sessions()
    app = create_app(static_dir=None, db_path=db_file)
    c = TestClient(app, raise_server_exceptions=False)
    resp = c.post("/api/auth/login", json={"username": "user", "password": "password"})
    token = resp.json()["token"]
    c.get("/api/board", headers={"Authorization": f"Bearer {token}"})
    assert db_file.exists()


def test_all_board_routes_require_auth(client):
    """All board endpoints return 401/422 without a token."""
    endpoints = [
        ("GET", "/api/board"),
        ("PUT", "/api/board/columns/col-backlog"),
        ("POST", "/api/board/cards"),
        ("PUT", "/api/board/cards/card-1"),
        ("DELETE", "/api/board/cards/card-1"),
        ("PUT", "/api/board/cards/card-1/move"),
        ("PUT", "/api/board"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code in (401, 422), f"{method} {path} returned {resp.status_code}"
