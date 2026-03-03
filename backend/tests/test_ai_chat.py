import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai import AIResponse, BoardAction


def _mock_ai_response(response_text, board_updates=None):
    """Create a mock that makes chat() return a structured JSON string."""
    data = {"response": response_text, "board_updates": board_updates or []}
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(data)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# -- Structured output parsing tests --


def test_chat_response_only(auth_client):
    """AI returns text with no board updates."""
    mock_resp = _mock_ai_response("Hello! How can I help?")
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Hi"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Hello! How can I help?"
    assert body["board_updates"] == []


def test_chat_create_card(auth_client):
    """AI creates a card; verify it appears in the DB."""
    mock_resp = _mock_ai_response("Done!", [
        {"action": "create_card", "column_id": "col-backlog", "card_id": "card-new1", "title": "Testing"},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Add a card"})

    assert resp.status_code == 200
    assert len(resp.json()["board_updates"]) == 1

    # Verify card exists in the board
    board = auth_client.get("/api/board").json()
    assert "card-new1" in board["cards"]
    assert board["cards"]["card-new1"]["title"] == "Testing"


def test_chat_edit_card(auth_client):
    """AI edits an existing card."""
    mock_resp = _mock_ai_response("Updated!", [
        {"action": "edit_card", "card_id": "card-1", "title": "New Title", "details": "New details"},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Edit card-1"})

    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert board["cards"]["card-1"]["title"] == "New Title"
    assert board["cards"]["card-1"]["details"] == "New details"


def test_chat_delete_card(auth_client):
    """AI deletes a card."""
    mock_resp = _mock_ai_response("Deleted!", [
        {"action": "delete_card", "card_id": "card-1"},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Delete card-1"})

    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    assert "card-1" not in board["cards"]


def test_chat_move_card(auth_client):
    """AI moves a card to a different column."""
    mock_resp = _mock_ai_response("Moved!", [
        {"action": "move_card", "card_id": "card-1", "column_id": "col-done", "position": 0},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Move card-1 to Done"})

    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    done_col = next(c for c in board["columns"] if c["id"] == "col-done")
    assert "card-1" in done_col["cardIds"]


def test_chat_rename_column(auth_client):
    """AI renames a column."""
    mock_resp = _mock_ai_response("Renamed!", [
        {"action": "rename_column", "column_id": "col-backlog", "title": "To Do"},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Rename Backlog to To Do"})

    assert resp.status_code == 200
    board = auth_client.get("/api/board").json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert backlog["title"] == "To Do"


def test_chat_multiple_updates(auth_client):
    """AI returns several actions in one response."""
    mock_resp = _mock_ai_response("Done both!", [
        {"action": "create_card", "column_id": "col-backlog", "card_id": "card-multi1", "title": "Card A"},
        {"action": "rename_column", "column_id": "col-done", "title": "Completed"},
    ])
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_resp
        resp = auth_client.post("/api/ai/chat", json={"message": "Do two things"})

    assert resp.status_code == 200
    assert len(resp.json()["board_updates"]) == 2

    board = auth_client.get("/api/board").json()
    assert "card-multi1" in board["cards"]
    done_col = next(c for c in board["columns"] if c["id"] == "col-done")
    assert done_col["title"] == "Completed"


def test_chat_invalid_json_fallback(auth_client):
    """When AI returns plain text, fall back to response-only."""
    mock_choice = MagicMock()
    mock_choice.message.content = "I'm not sure what you mean."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_response
        resp = auth_client.post("/api/ai/chat", json={"message": "???"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "I'm not sure what you mean."
    assert body["board_updates"] == []


def test_chat_requires_auth(client):
    """Chat endpoint returns 401/422 without a token."""
    resp = client.post("/api/ai/chat", json={"message": "Hi"})
    assert resp.status_code in (401, 422)


def test_chat_conversation_history(auth_client):
    """Second message should include conversation history in the AI call."""
    mock_resp1 = _mock_ai_response("First reply")
    mock_resp2 = _mock_ai_response("Second reply")

    with patch("app.ai._get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create
        mock_create.side_effect = [mock_resp1, mock_resp2]

        auth_client.post("/api/ai/chat", json={"message": "Hello"})
        auth_client.post("/api/ai/chat", json={"message": "Follow up"})

        # Second call should have history from the first exchange
        second_call_messages = mock_create.call_args_list[1].kwargs["messages"]
        # Should contain: system prompt, user "Hello", assistant "First reply", user "Follow up"
        roles = [m["role"] for m in second_call_messages]
        assert "system" in roles
        assert roles.count("user") == 2
        assert roles.count("assistant") == 1
