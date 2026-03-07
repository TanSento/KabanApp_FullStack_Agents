import json
import os
import uuid

from openai import APIError, APITimeoutError, OpenAI
from pydantic import BaseModel


MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT_TEMPLATE = """\
You are a helpful Kanban board assistant. The user's current board state is:

{board_json}

You can help the user by answering questions and optionally making changes to the board.

Available actions (use in board_updates):
- create_card: requires column_id, card_id (generate a "card-" + 8 hex chars ID), title; optional details
- edit_card: requires card_id, title, details
- delete_card: requires card_id
- move_card: requires card_id, column_id (target), position (0-indexed)
- rename_column: requires column_id, title

IMPORTANT: In your "response" text, never show internal IDs like card-xxx or col-xxx. Refer to cards and columns by their titles only. Keep responses concise and friendly.

Always respond with valid JSON in this exact format:
{{"response": "your text response to the user", "board_updates": [...]}}

If no board changes are needed, use an empty board_updates list:
{{"response": "your answer", "board_updates": []}}
"""


class BoardAction(BaseModel):
    action: str
    column_id: str | None = None
    card_id: str | None = None
    title: str | None = None
    details: str | None = None
    position: int | None = None
    due_date: str | None = None
    priority: str | None = None


class AIResponse(BaseModel):
    response: str
    board_updates: list[BoardAction] = []


class AIServiceError(Exception):
    """Raised when the AI service returns an error."""


class AINotConfiguredError(Exception):
    """Raised when the API key is missing."""


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise AINotConfiguredError("OPENROUTER_API_KEY is not set")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def chat(messages: list[dict[str, str]]) -> str:
    """Send messages to the AI model and return the response text."""
    client = _get_client()
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return response.choices[0].message.content
    except (APIError, APITimeoutError) as exc:
        raise AIServiceError(f"AI service error: {exc}") from exc


def chat_with_board(
    board_state: dict,
    message: str,
    conversation_history: list[dict[str, str]],
) -> AIResponse:
    """Send a chat message with board context and return a structured response."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        board_json=json.dumps(board_state, indent=2),
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": message})

    raw = chat(messages)

    # Try to parse structured JSON response
    try:
        # Handle markdown-wrapped JSON (```json ... ```)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # drop opening ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        data = json.loads(text)
        return AIResponse(**data)
    except (json.JSONDecodeError, ValueError, TypeError):
        return AIResponse(response=raw, board_updates=[])
