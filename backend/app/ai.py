import os

from openai import OpenAI, APIError, APITimeoutError


MODEL = "openai/gpt-oss-120b"


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
