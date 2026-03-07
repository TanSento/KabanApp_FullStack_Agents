"""End-to-end flow test: login, get board, modify, verify persistence."""


def test_e2e_flow(client):
    # Login
    resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get initial board
    resp = client.get("/api/board", headers=headers)
    assert resp.status_code == 200
    board = resp.json()
    assert len(board["columns"]) == 5
    assert len(board["cards"]) == 8

    # Get dynamic IDs from the board
    col_map = {col["title"]: col["id"] for col in board["columns"]}
    backlog_id = col_map["Backlog"]
    done_id = col_map["Done"]
    review_id = col_map["Review"]

    card_map = {card["title"]: cid for cid, card in board["cards"].items()}
    card1_id = card_map["Align roadmap themes"]
    card2_id = card_map["Gather customer signals"]

    # Rename a column
    resp = client.put(f"/api/board/columns/{backlog_id}", headers=headers, json={"title": "To Do"})
    assert resp.status_code == 200

    # Add a card
    resp = client.post("/api/board/cards", headers=headers, json={
        "column_id": done_id,
        "id": "card-e2e",
        "title": "E2E card",
        "details": "Created in e2e test",
    })
    assert resp.status_code == 200

    # Move a card
    resp = client.put(f"/api/board/cards/{card1_id}/move", headers=headers, json={
        "column_id": review_id,
        "position": 0,
    })
    assert resp.status_code == 200

    # Delete a card
    resp = client.delete(f"/api/board/cards/{card2_id}", headers=headers)
    assert resp.status_code == 200

    # Verify persistence
    resp = client.get("/api/board", headers=headers)
    assert resp.status_code == 200
    board = resp.json()

    # Column was renamed
    backlog = next(c for c in board["columns"] if c["id"] == backlog_id)
    assert backlog["title"] == "To Do"

    # Card was added
    assert "card-e2e" in board["cards"]
    done = next(c for c in board["columns"] if c["id"] == done_id)
    assert "card-e2e" in done["cardIds"]

    # Card was moved
    review = next(c for c in board["columns"] if c["id"] == review_id)
    assert card1_id in review["cardIds"]
    assert card1_id not in backlog["cardIds"]

    # Card was deleted
    assert card2_id not in board["cards"]
    assert card2_id not in backlog["cardIds"]

    # Total cards: 8 original - 1 deleted + 1 added = 8
    assert len(board["cards"]) == 8
