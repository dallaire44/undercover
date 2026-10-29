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


def decide(client, claim_id, decision="approve", payout=420.0):
    """Record a decision on a claim."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": "The wording covers it.",
        "policy_section": "3. Trip Delay",
    }
    return client.post(f"/api/claims/{claim_id}/decision", json=body)


def pay(client, claim_id, amount):
    """Try to pay a claim."""
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def status(client, claim_id):
    """Return a claim's state."""
    return client.get(f"/api/claims/{claim_id}").json()["status"]
