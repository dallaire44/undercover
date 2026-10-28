import pytest

from backend import runs


@pytest.fixture
def agent(client, monkeypatch):
    """Replace the agent with one that records what it saw and declines the claim."""
    seen = []

    def decline(claim_id, thread_id):
        seen.append((claim_id, client.get(f"/api/claims/{claim_id}").json()["status"]))
        body = {
            "decision": "decline",
            "payout": 0,
            "reason": "Not covered.",
            "policy_section": "Section 9",
        }
        client.post(f"/api/claims/{claim_id}/decision", json=body)

    monkeypatch.setattr(runs, "agent_run", decline)
    return seen


def steps(client, claim_id):
    return [s["text"] for s in client.get(f"/api/claims/{claim_id}/steps").json()]


def test_start_agent_runs_in_the_background(client, agent):
    response = client.post("/api/claims/CLM-1001/agent")
    assert response.status_code == 202
    assert response.json()["status"] == "in_progress"
    assert agent == [("CLM-1001", "in_progress")]
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert steps(client, "CLM-1001") == ["Agent started", "Agent finished"]


def test_start_agent_needs_a_waiting_claim(client, agent):
    client.post("/api/claims/CLM-1001/agent")
    assert client.post("/api/claims/CLM-1001/agent").status_code == 409
    assert client.post("/api/claims/CLM-9999/agent").status_code == 404


def test_run_without_a_decision_puts_the_claim_back(client, monkeypatch):
    monkeypatch.setattr(runs, "agent_run", lambda claim_id, thread_id: "done")
    client.post("/api/claims/CLM-1001/agent")
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"
    assert steps(client, "CLM-1001") == [
        "Agent started",
        "Agent finished without a decision",
        "Agent finished",
    ]


def test_failed_run_puts_the_claim_back(client, monkeypatch):
    def fail(claim_id, thread_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(runs, "agent_run", fail)
    client.post("/api/claims/CLM-1001/agent")
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"
    assert "Agent failed: boom" in steps(client, "CLM-1001")


def test_work_queue_runs_every_waiting_claim_in_turn(client, agent):
    client.post("/api/claims/CLM-1002/agent")
    response = client.post("/api/queue/agent")
    assert response.status_code == 202
    assert len(response.json()) == 24
    assert [claim_id for claim_id, _ in agent][1:] == response.json()
    statuses = {c["status"] for c in client.get("/api/claims").json()}
    assert statuses == {"decided"}
