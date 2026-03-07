"""Tests for multi-board management and user registration."""


# -- User registration --

def test_register_new_user(client):
    resp = client.post("/api/auth/register", json={"username": "newuser", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "newuser"


def test_register_duplicate_username(client):
    client.post("/api/auth/register", json={"username": "dupuser", "password": "secret123"})
    resp = client.post("/api/auth/register", json={"username": "dupuser", "password": "other123"})
    assert resp.status_code == 409


def test_register_short_username(client):
    resp = client.post("/api/auth/register", json={"username": "ab", "password": "secret123"})
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post("/api/auth/register", json={"username": "validuser", "password": "abc"})
    assert resp.status_code == 400


def test_registered_user_can_login(client):
    client.post("/api/auth/register", json={"username": "reguser", "password": "mypassword"})
    resp = client.post("/api/auth/login", json={"username": "reguser", "password": "mypassword"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "reguser"


def test_registered_user_wrong_password(client):
    client.post("/api/auth/register", json={"username": "reguser2", "password": "mypassword"})
    resp = client.post("/api/auth/login", json={"username": "reguser2", "password": "wrongpass"})
    assert resp.status_code == 401


def test_registered_user_gets_board(client):
    reg_resp = client.post("/api/auth/register", json={"username": "boarduser", "password": "mypassword"})
    token = reg_resp.json()["token"]
    resp = client.get("/api/board", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 5


# -- Multi-board management --

def test_list_boards(auth_client):
    resp = auth_client.get("/api/boards")
    assert resp.status_code == 200
    data = resp.json()
    assert "boards" in data
    assert len(data["boards"]) >= 1
    assert "id" in data["boards"][0]
    assert "title" in data["boards"][0]


def test_create_board(auth_client):
    resp = auth_client.post("/api/boards", json={"title": "Sprint Board"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Sprint Board"
    assert "id" in data

    boards_resp = auth_client.get("/api/boards")
    titles = [b["title"] for b in boards_resp.json()["boards"]]
    assert "Sprint Board" in titles


def test_create_board_empty_title(auth_client):
    resp = auth_client.post("/api/boards", json={"title": "  "})
    assert resp.status_code == 400


def test_get_board_by_id(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert "cards" in data


def test_get_board_by_id_not_found(auth_client):
    resp = auth_client.get("/api/boards/99999")
    assert resp.status_code == 404


def test_rename_board(auth_client):
    create_resp = auth_client.post("/api/boards", json={"title": "Old Name"})
    board_id = create_resp.json()["id"]

    resp = auth_client.patch(f"/api/boards/{board_id}", json={"title": "New Name"})
    assert resp.status_code == 200

    boards = auth_client.get("/api/boards").json()["boards"]
    titles = [b["title"] for b in boards]
    assert "New Name" in titles
    assert "Old Name" not in titles


def test_rename_board_not_found(auth_client):
    resp = auth_client.patch("/api/boards/99999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_delete_board(auth_client):
    # Create a second board first
    create_resp = auth_client.post("/api/boards", json={"title": "Temp Board"})
    board_id = create_resp.json()["id"]

    resp = auth_client.delete(f"/api/boards/{board_id}")
    assert resp.status_code == 200

    boards = auth_client.get("/api/boards").json()["boards"]
    ids = [b["id"] for b in boards]
    assert board_id not in ids


def test_cannot_delete_last_board(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    assert len(boards) == 1
    board_id = boards[0]["id"]
    resp = auth_client.delete(f"/api/boards/{board_id}")
    assert resp.status_code == 400


def test_delete_board_not_found(auth_client):
    resp = auth_client.delete("/api/boards/99999")
    assert resp.status_code == 404


def test_second_board_has_seeded_data(auth_client):
    create_resp = auth_client.post("/api/boards", json={"title": "Board Two"})
    board_id = create_resp.json()["id"]
    resp = auth_client.get(f"/api/boards/{board_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 5
    assert len(data["cards"]) == 8


# -- Column management on specific board --

def test_create_column_on_board(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]

    resp = auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "Ice Box"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Ice Box"
    assert "id" in data

    board = auth_client.get(f"/api/boards/{board_id}").json()
    titles = [c["title"] for c in board["columns"]]
    assert "Ice Box" in titles


def test_create_column_empty_title(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.post(f"/api/boards/{board_id}/columns", json={"title": ""})
    assert resp.status_code == 400


def test_delete_column_on_board(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]

    # Create a column to delete
    col_resp = auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "To Delete"})
    col_id = col_resp.json()["id"]

    resp = auth_client.delete(f"/api/boards/{board_id}/columns/{col_id}")
    assert resp.status_code == 200

    board = auth_client.get(f"/api/boards/{board_id}").json()
    titles = [c["title"] for c in board["columns"]]
    assert "To Delete" not in titles


def test_delete_column_not_found(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.delete(f"/api/boards/{board_id}/columns/col-nonexistent")
    assert resp.status_code == 404


# -- Board-specific card operations --

def test_crud_on_specific_board(auth_client):
    create_resp = auth_client.post("/api/boards", json={"title": "Card Test Board"})
    board_id = create_resp.json()["id"]

    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_col_id = board["columns"][0]["id"]

    # Create card
    resp = auth_client.post(f"/api/boards/{board_id}/cards", json={
        "column_id": first_col_id,
        "id": "test-card-42",
        "title": "Test card",
        "details": "Details here",
    })
    assert resp.status_code == 200

    # Verify card appears
    board = auth_client.get(f"/api/boards/{board_id}").json()
    assert "test-card-42" in board["cards"]

    # Update card
    resp = auth_client.put(f"/api/boards/{board_id}/cards/test-card-42", json={
        "title": "Updated title",
        "details": "New details",
    })
    assert resp.status_code == 200

    # Delete card
    resp = auth_client.delete(f"/api/boards/{board_id}/cards/test-card-42")
    assert resp.status_code == 200

    board = auth_client.get(f"/api/boards/{board_id}").json()
    assert "test-card-42" not in board["cards"]


def test_board_isolation(auth_client):
    """Cards from one board should not appear in another."""
    board_a = auth_client.post("/api/boards", json={"title": "Board A"}).json()["id"]
    board_b = auth_client.post("/api/boards", json={"title": "Board B"}).json()["id"]

    col_a = auth_client.get(f"/api/boards/{board_a}").json()["columns"][0]["id"]

    auth_client.post(f"/api/boards/{board_a}/cards", json={
        "column_id": col_a, "id": "card-isolation-test", "title": "Only in A", "details": "",
    })

    board_b_data = auth_client.get(f"/api/boards/{board_b}").json()
    assert "card-isolation-test" not in board_b_data["cards"]


def test_all_boards_routes_require_auth(client):
    """All /api/boards endpoints return 401/422 without a token."""
    endpoints = [
        ("GET", "/api/boards"),
        ("POST", "/api/boards"),
        ("GET", "/api/boards/1"),
        ("PATCH", "/api/boards/1"),
        ("DELETE", "/api/boards/1"),
        ("POST", "/api/boards/1/columns"),
        ("DELETE", "/api/boards/1/columns/col-any"),
        ("POST", "/api/boards/1/cards"),
        ("PUT", "/api/boards/1/cards/card-any"),
        ("DELETE", "/api/boards/1/cards/card-any"),
        ("PUT", "/api/boards/1/cards/card-any/move"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code in (401, 422), f"{method} {path} returned {resp.status_code}"
