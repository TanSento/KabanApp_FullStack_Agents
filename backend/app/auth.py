import uuid

VALID_USERNAME = "user"
VALID_PASSWORD = "password"

# In-memory session store: token -> username
_sessions: dict[str, str] = {}


def login(username: str, password: str) -> str | None:
    """Validate credentials and return a session token, or None on failure."""
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        token = uuid.uuid4().hex
        _sessions[token] = username
        return token
    return None


def logout(token: str) -> bool:
    """Invalidate a session token. Returns True if the token existed."""
    return _sessions.pop(token, None) is not None


def get_user(token: str) -> str | None:
    """Return the username for a valid token, or None."""
    return _sessions.get(token)


def clear_sessions() -> None:
    """Clear all sessions. Used in tests."""
    _sessions.clear()
