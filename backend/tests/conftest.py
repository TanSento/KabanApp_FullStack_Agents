import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Client for the app without a static directory (API-only mode)."""
    return TestClient(create_app(static_dir=None))
