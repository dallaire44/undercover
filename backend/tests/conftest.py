import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client on its own temporary database."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    return TestClient(app)
