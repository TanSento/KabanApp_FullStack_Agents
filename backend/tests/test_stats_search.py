"""Tests for board stats and card search endpoints."""


def test_board_stats_returns_correct_totals(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_priority" in data
    assert "overdue" in data
    # Seeded board has 8 cards
    assert data["total"] == 8


def test_board_stats_by_priority_all_none_by_default(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    data = auth_client.get(f"/api/boards/{board_id}/stats").json()
    # All seeded cards have priority "none"
    assert data["by_priority"].get("none", 0) == 8


def test_board_stats_after_adding_priority_cards(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = board["columns"][0]["id"]

    auth_client.post(f"/api/boards/{board_id}/cards", json={
        "column_id": col_id,
        "id": "card-stats-1",
        "title": "High priority task",
        "priority": "high",
    })
    auth_client.post(f"/api/boards/{board_id}/cards", json={
        "column_id": col_id,
        "id": "card-stats-2",
        "title": "Urgent task",
        "priority": "urgent",
    })

    data = auth_client.get(f"/api/boards/{board_id}/stats").json()
    assert data["by_priority"].get("high", 0) == 1
    assert data["by_priority"].get("urgent", 0) == 1
    assert data["total"] == 10


def test_board_stats_requires_auth(client):
    resp = client.get("/api/boards/1/stats")
    assert resp.status_code in (401, 422)


def test_board_stats_not_found(auth_client):
    resp = auth_client.get("/api/boards/999/stats")
    assert resp.status_code == 404


def test_search_cards_returns_matches(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/search?q=roadmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert len(data["cards"]) >= 1
    assert any("roadmap" in card["title"].lower() or "roadmap" in card["details"].lower() for card in data["cards"])


def test_search_cards_case_insensitive(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/search?q=ROADMAP")
    assert resp.status_code == 200
    assert len(resp.json()["cards"]) >= 1


def test_search_cards_no_match(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/search?q=zzz_no_match_xyz")
    assert resp.status_code == 200
    assert resp.json()["cards"] == []


def test_search_cards_empty_query(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/search?q=")
    assert resp.status_code == 200
    assert resp.json()["cards"] == []


def test_search_cards_requires_auth(client):
    resp = client.get("/api/boards/1/search?q=test")
    assert resp.status_code in (401, 422)


def test_search_cards_not_found(auth_client):
    resp = auth_client.get("/api/boards/999/search?q=test")
    assert resp.status_code == 404


def test_search_by_details(auth_client):
    boards = auth_client.get("/api/boards").json()["boards"]
    board_id = boards[0]["id"]
    # "quarterly" appears in card details
    resp = auth_client.get(f"/api/boards/{board_id}/search?q=quarterly")
    assert resp.status_code == 200
    assert len(resp.json()["cards"]) >= 1
