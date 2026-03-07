"""Tests for board labels and card label assignments."""


def _setup(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = list(board["cards"].keys())[0]
    return board_id, card_id


def test_get_labels_empty(auth_client):
    board_id, _ = _setup(auth_client)
    resp = auth_client.get(f"/api/boards/{board_id}/labels")
    assert resp.status_code == 200
    assert resp.json()["labels"] == []


def test_create_label(auth_client):
    board_id, _ = _setup(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Bug", "color": "#ef4444"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Bug"
    assert data["color"] == "#ef4444"
    assert "id" in data


def test_create_label_default_color(auth_client):
    board_id, _ = _setup(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Feature"})
    assert resp.status_code == 200
    assert resp.json()["color"] == "#6366f1"


def test_create_label_empty_name_rejected(auth_client):
    board_id, _ = _setup(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "  "})
    assert resp.status_code == 400


def test_list_labels(auth_client):
    board_id, _ = _setup(auth_client)
    auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Label A"})
    auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Label B"})
    resp = auth_client.get(f"/api/boards/{board_id}/labels")
    labels = resp.json()["labels"]
    assert len(labels) == 2
    names = [l["name"] for l in labels]
    assert "Label A" in names
    assert "Label B" in names


def test_delete_label(auth_client):
    board_id, _ = _setup(auth_client)
    label = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Temp"}).json()
    resp = auth_client.delete(f"/api/boards/{board_id}/labels/{label['id']}")
    assert resp.status_code == 200
    labels = auth_client.get(f"/api/boards/{board_id}/labels").json()["labels"]
    assert not any(l["id"] == label["id"] for l in labels)


def test_delete_label_not_found(auth_client):
    board_id, _ = _setup(auth_client)
    resp = auth_client.delete(f"/api/boards/{board_id}/labels/999999")
    assert resp.status_code == 404


def test_get_card_labels_empty(auth_client):
    board_id, card_id = _setup(auth_client)
    resp = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/labels")
    assert resp.status_code == 200
    assert resp.json()["labels"] == []


def test_set_card_label(auth_client):
    board_id, card_id = _setup(auth_client)
    label = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "Important"}).json()
    resp = auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/labels/{label['id']}")
    assert resp.status_code == 200
    labels = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/labels").json()["labels"]
    assert len(labels) == 1
    assert labels[0]["name"] == "Important"


def test_set_card_label_idempotent(auth_client):
    board_id, card_id = _setup(auth_client)
    label = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "X"}).json()
    auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/labels/{label['id']}")
    auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/labels/{label['id']}")
    labels = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/labels").json()["labels"]
    assert len(labels) == 1


def test_remove_card_label(auth_client):
    board_id, card_id = _setup(auth_client)
    label = auth_client.post(f"/api/boards/{board_id}/labels", json={"name": "ToRemove"}).json()
    auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/labels/{label['id']}")
    resp = auth_client.delete(f"/api/boards/{board_id}/cards/{card_id}/labels/{label['id']}")
    assert resp.status_code == 200
    labels = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/labels").json()["labels"]
    assert labels == []


def test_set_label_wrong_board_rejected(auth_client):
    """Label from board A cannot be applied to card from board B."""
    # Create second board
    board2 = auth_client.post("/api/boards", json={"title": "Board 2"}).json()
    board2_id = board2["id"]

    board1_id, card1_id = _setup(auth_client)
    # Create label on board 2
    label = auth_client.post(f"/api/boards/{board2_id}/labels", json={"name": "B2 Label"}).json()

    # Try to assign board2's label to board1's card
    resp = auth_client.post(f"/api/boards/{board1_id}/cards/{card1_id}/labels/{label['id']}")
    assert resp.status_code == 404


def test_labels_require_auth(client):
    resp = client.get("/api/boards/1/labels")
    assert resp.status_code in (401, 422)
