from unittest.mock import MagicMock, patch

import pytest
from openai import APIError, APITimeoutError

from app.ai import AINotConfiguredError, AIServiceError, chat


# -- Unit tests for the chat() function --


def test_chat_returns_response_text():
    mock_choice = MagicMock()
    mock_choice.message.content = "4"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_response
        result = chat([{"role": "user", "content": "What is 2+2?"}])

    assert result == "4"
    mock_get.return_value.chat.completions.create.assert_called_once_with(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )


def test_chat_raises_on_missing_api_key():
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False):
        with pytest.raises(AINotConfiguredError):
            chat([{"role": "user", "content": "hi"}])


def test_chat_raises_on_api_error():
    mock_request = MagicMock()
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.side_effect = APIError(
            message="rate limited", request=mock_request, body=None,
        )
        with pytest.raises(AIServiceError, match="AI service error"):
            chat([{"role": "user", "content": "hi"}])


def test_chat_raises_on_timeout():
    mock_request = MagicMock()
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.side_effect = APITimeoutError(
            request=mock_request,
        )
        with pytest.raises(AIServiceError, match="AI service error"):
            chat([{"role": "user", "content": "hi"}])


# -- API endpoint tests --


def test_ai_test_endpoint_returns_response(auth_client):
    mock_choice = MagicMock()
    mock_choice.message.content = "4"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = mock_response
        resp = auth_client.post("/api/ai/test")

    assert resp.status_code == 200
    assert resp.json() == {"response": "4"}


def test_ai_test_endpoint_503_when_not_configured(auth_client):
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False):
        resp = auth_client.post("/api/ai/test")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "AI service not configured"


def test_ai_test_endpoint_502_on_api_error(auth_client):
    mock_request = MagicMock()
    with patch("app.ai._get_client") as mock_get:
        mock_get.return_value.chat.completions.create.side_effect = APIError(
            message="service down", request=mock_request, body=None,
        )
        resp = auth_client.post("/api/ai/test")

    assert resp.status_code == 502
    assert "AI service error" in resp.json()["detail"]


def test_ai_test_endpoint_requires_auth(client):
    resp = client.post("/api/ai/test")
    assert resp.status_code == 422 or resp.status_code == 401
