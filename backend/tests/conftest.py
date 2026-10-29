import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client on its own seeded database."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    db.init()
    return TestClient(app)
