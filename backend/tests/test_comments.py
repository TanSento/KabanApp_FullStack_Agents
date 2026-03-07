"""Tests for card comments feature."""


def _get_board_and_card(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_card_id = list(board["cards"].keys())[0]
    return board_id, first_card_id


def test_get_comments_empty(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    resp = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/comments")
    assert resp.status_code == 200
    assert resp.json()["comments"] == []


def test_add_comment(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "This is a comment"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["body"] == "This is a comment"
    assert "id" in data
    assert "created_at" in data
    assert "username" in data


def test_comments_persist_and_are_listed(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "First comment"})
    auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "Second comment"})
    resp = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/comments")
    comments = resp.json()["comments"]
    assert len(comments) == 2
    assert comments[0]["body"] == "First comment"
    assert comments[1]["body"] == "Second comment"


def test_delete_comment(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    comment = auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "To delete"}).json()
    comment_id = comment["id"]

    resp = auth_client.delete(f"/api/boards/{board_id}/cards/{card_id}/comments/{comment_id}")
    assert resp.status_code == 200

    comments = auth_client.get(f"/api/boards/{board_id}/cards/{card_id}/comments").json()["comments"]
    assert not any(c["id"] == comment_id for c in comments)


def test_delete_comment_not_found(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    resp = auth_client.delete(f"/api/boards/{board_id}/cards/{card_id}/comments/999999")
    assert resp.status_code == 404


def test_add_empty_comment_rejected(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "  "})
    assert resp.status_code == 400


def test_get_comments_card_not_found(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/cards/nonexistent-card/comments")
    assert resp.status_code == 404


def test_add_comment_card_not_found(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.post(f"/api/boards/{board_id}/cards/nonexistent-card/comments", json={"body": "Hello"})
    assert resp.status_code == 404


def test_comments_require_auth(client):
    resp = client.get("/api/boards/1/cards/card-1/comments")
    assert resp.status_code in (401, 422)


def test_comment_includes_username(auth_client):
    board_id, card_id = _get_board_and_card(auth_client)
    resp = auth_client.post(f"/api/boards/{board_id}/cards/{card_id}/comments", json={"body": "Test"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "user"
