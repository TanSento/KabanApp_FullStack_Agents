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

    # Rename a column
    resp = client.put("/api/board/columns/col-backlog", headers=headers, json={"title": "To Do"})
    assert resp.status_code == 200

    # Add a card
    resp = client.post("/api/board/cards", headers=headers, json={
        "column_id": "col-done",
        "id": "card-e2e",
        "title": "E2E card",
        "details": "Created in e2e test",
    })
    assert resp.status_code == 200

    # Move a card
    resp = client.put("/api/board/cards/card-1/move", headers=headers, json={
        "column_id": "col-review",
        "position": 0,
    })
    assert resp.status_code == 200

    # Delete a card
    resp = client.delete("/api/board/cards/card-2", headers=headers)
    assert resp.status_code == 200

    # Verify persistence
    resp = client.get("/api/board", headers=headers)
    assert resp.status_code == 200
    board = resp.json()

    # Column was renamed
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert backlog["title"] == "To Do"

    # Card was added
    assert "card-e2e" in board["cards"]
    done = next(c for c in board["columns"] if c["id"] == "col-done")
    assert "card-e2e" in done["cardIds"]

    # Card was moved
    review = next(c for c in board["columns"] if c["id"] == "col-review")
    assert "card-1" in review["cardIds"]
    assert "card-1" not in backlog["cardIds"]

    # Card was deleted
    assert "card-2" not in board["cards"]
    assert "card-2" not in backlog["cardIds"]

    # Total cards: 8 original - 1 deleted + 1 added = 8
    assert len(board["cards"]) == 8
