"""Tests for card due dates, priorities, and column reordering."""


# -- Card due dates and priorities --

def test_create_card_with_due_date_and_priority(auth_client, col_ids):
    backlog_id = col_ids["Backlog"]
    resp = auth_client.post("/api/board/cards", json={
        "column_id": backlog_id,
        "id": "card-featured-1",
        "title": "Task with metadata",
        "details": "Has date and priority",
        "due_date": "2026-04-01",
        "priority": "high",
    })
    assert resp.status_code == 200

    board = auth_client.get("/api/board").json()
    card = board["cards"]["card-featured-1"]
    assert card["due_date"] == "2026-04-01"
    assert card["priority"] == "high"


def test_create_card_default_priority(auth_client, col_ids):
    backlog_id = col_ids["Backlog"]
    resp = auth_client.post("/api/board/cards", json={
        "column_id": backlog_id,
        "id": "card-default-priority",
        "title": "Default priority card",
    })
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert board["cards"]["card-default-priority"]["priority"] == "none"
    assert board["cards"]["card-default-priority"]["due_date"] is None


def test_update_card_with_due_date_and_priority(auth_client, card_ids):
    card_id = card_ids["Align roadmap themes"]
    resp = auth_client.put(f"/api/board/cards/{card_id}", json={
        "title": "Updated with meta",
        "details": "Now has due date",
        "due_date": "2026-05-15",
        "priority": "urgent",
    })
    assert resp.status_code == 200

    board = auth_client.get("/api/board").json()
    card = board["cards"][card_id]
    assert card["due_date"] == "2026-05-15"
    assert card["priority"] == "urgent"
    assert card["title"] == "Updated with meta"


def test_update_card_clear_due_date(auth_client, card_ids):
    card_id = card_ids["Align roadmap themes"]
    # Set a due date first
    auth_client.put(f"/api/board/cards/{card_id}", json={
        "title": "Task",
        "details": "",
        "due_date": "2026-04-01",
        "priority": "low",
    })
    # Clear it
    resp = auth_client.put(f"/api/board/cards/{card_id}", json={
        "title": "Task",
        "details": "",
        "due_date": None,
        "priority": "none",
    })
    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert board["cards"][card_id]["due_date"] is None
    assert board["cards"][card_id]["priority"] == "none"


def test_all_priority_values_accepted(auth_client, col_ids):
    backlog_id = col_ids["Backlog"]
    for i, priority in enumerate(["none", "low", "medium", "high", "urgent"]):
        resp = auth_client.post("/api/board/cards", json={
            "column_id": backlog_id,
            "id": f"card-priority-{i}",
            "title": f"Card {priority}",
            "priority": priority,
        })
        assert resp.status_code == 200, f"Priority {priority} should be accepted"


def test_invalid_priority_rejected(auth_client, col_ids):
    backlog_id = col_ids["Backlog"]
    resp = auth_client.post("/api/board/cards", json={
        "column_id": backlog_id,
        "id": "card-bad-priority",
        "title": "Bad priority",
        "priority": "critical",  # invalid
    })
    assert resp.status_code == 400


def test_board_response_includes_due_date_and_priority(auth_client):
    board = auth_client.get("/api/board").json()
    # All cards should have due_date and priority fields
    for card in board["cards"].values():
        assert "due_date" in card
        assert "priority" in card


def test_board_specific_card_with_due_date(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_col_id = board["columns"][0]["id"]

    resp = auth_client.post(f"/api/boards/{board_id}/cards", json={
        "column_id": first_col_id,
        "id": "card-board-specific",
        "title": "Board specific card",
        "details": "",
        "due_date": "2026-06-30",
        "priority": "medium",
    })
    assert resp.status_code == 200

    board_data = auth_client.get(f"/api/boards/{board_id}").json()
    card = board_data["cards"]["card-board-specific"]
    assert card["due_date"] == "2026-06-30"
    assert card["priority"] == "medium"


def test_board_specific_update_card_priority(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_card_id = list(board["cards"].keys())[0]

    resp = auth_client.put(f"/api/boards/{board_id}/cards/{first_card_id}", json={
        "title": "Updated",
        "details": "",
        "due_date": "2026-07-01",
        "priority": "high",
    })
    assert resp.status_code == 200

    updated_board = auth_client.get(f"/api/boards/{board_id}").json()
    assert updated_board["cards"][first_card_id]["priority"] == "high"


def test_board_specific_invalid_priority_rejected(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_col_id = board["columns"][0]["id"]

    resp = auth_client.post(f"/api/boards/{board_id}/cards", json={
        "column_id": first_col_id,
        "id": "card-invalid",
        "title": "Bad",
        "priority": "super-high",
    })
    assert resp.status_code == 400


# -- Column reordering --

def test_reorder_columns(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_ids_in_order = [col["id"] for col in board["columns"]]

    # Reverse the column order
    reversed_ids = list(reversed(col_ids_in_order))
    resp = auth_client.put(f"/api/boards/{board_id}/columns/reorder", json={"column_ids": reversed_ids})
    assert resp.status_code == 200

    updated_board = auth_client.get(f"/api/boards/{board_id}").json()
    updated_order = [col["id"] for col in updated_board["columns"]]
    assert updated_order == reversed_ids


def test_reorder_columns_partial_ids_rejected(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_ids_in_order = [col["id"] for col in board["columns"]]

    # Omit one column
    partial_ids = col_ids_in_order[:-1]
    resp = auth_client.put(f"/api/boards/{board_id}/columns/reorder", json={"column_ids": partial_ids})
    assert resp.status_code == 400


def test_reorder_columns_wrong_ids_rejected(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_ids_in_order = [col["id"] for col in board["columns"]]

    # Replace one with a fake ID
    fake_ids = col_ids_in_order[:-1] + ["col-nonexistent"]
    resp = auth_client.put(f"/api/boards/{board_id}/columns/reorder", json={"column_ids": fake_ids})
    assert resp.status_code == 400


def test_reorder_preserves_cards(auth_client):
    """Reordering columns doesn't affect card assignments."""
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_ids_in_order = [col["id"] for col in board["columns"]]
    card_counts = {col["id"]: len(col["cardIds"]) for col in board["columns"]}

    reversed_ids = list(reversed(col_ids_in_order))
    auth_client.put(f"/api/boards/{board_id}/columns/reorder", json={"column_ids": reversed_ids})

    updated_board = auth_client.get(f"/api/boards/{board_id}").json()
    for col in updated_board["columns"]:
        assert len(col["cardIds"]) == card_counts[col["id"]]
