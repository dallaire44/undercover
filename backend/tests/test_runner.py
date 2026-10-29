import pytest

from backend import runner
from backend.tests.conftest import decide, status


def step_texts(client, claim_id):
    return [s["text"] for s in client.get(f"/api/claims/{claim_id}/steps").json()]


@pytest.fixture
def deciding_agent(client, monkeypatch):
    """An agent that declines whatever claim it is given."""

    def run(claim_id, thread_id):
        decide(client, claim_id, "decline", 0.0)
        return "Declined."

    monkeypatch.setattr(runner, "run_agent", run)


def test_start_agent(client, deciding_agent):
    response = client.post("/api/claims/CLM-1001/agent")
    assert response.status_code == 202
    assert status(client, "CLM-1001") == "decided"
    texts = step_texts(client, "CLM-1001")
    assert texts[0] == "Agent started"
    assert texts[-1] == "Agent finished"


def test_start_agent_is_in_progress_while_running(client, monkeypatch):
    seen = []

    def run(claim_id, thread_id):
        seen.append(status(client, claim_id))
        decide(client, claim_id, "refer", 0.0)

    monkeypatch.setattr(runner, "run_agent", run)
    client.post("/api/claims/CLM-1001/agent")
    assert seen == ["in_progress"]


def test_start_agent_needs_a_waiting_claim(client, deciding_agent):
    client.post("/api/claims/CLM-1001/agent")
    assert client.post("/api/claims/CLM-1001/agent").status_code == 409
    assert client.post("/api/claims/CLM-9999/agent").status_code == 404


def test_run_without_a_decision_goes_back_to_waiting(client, monkeypatch):
    monkeypatch.setattr(runner, "run_agent", lambda claim_id, thread_id: "Hmm.")
    client.post("/api/claims/CLM-1001/agent")
    assert status(client, "CLM-1001") == "waiting"
    assert "without a decision" in step_texts(client, "CLM-1001")[-1]


def test_failed_run_goes_back_to_waiting(client, monkeypatch):
    def run(claim_id, thread_id):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(runner, "run_agent", run)
    client.post("/api/claims/CLM-1001/agent")
    assert status(client, "CLM-1001") == "waiting"
    assert "model unavailable" in step_texts(client, "CLM-1001")[-1]


def test_work_queue(client, deciding_agent):
    client.post("/api/claims/CLM-1001/agent")
    response = client.post("/api/queue/agent")
    assert response.status_code == 202
    assert len(response.json()) == 24
    claims = client.get("/api/claims").json()
    assert {c["status"] for c in claims} == {"decided"}
