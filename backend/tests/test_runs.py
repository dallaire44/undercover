import httpx
import pytest
from fastapi.testclient import TestClient

from backend import agent_service
from backend.main import app
from backend.tests.conftest import decide, status

REAL_POST = agent_service.post
DISPATCH = {"agents": 3, "model": "openai/gpt-6-luna", "reasoning_effort": "low"}


@pytest.fixture
def run_id(client):
    """A running dispatch, as the agent's service creates it."""
    return client.post("/api/dispatches", json=DISPATCH).json()["run_id"]


def take(client, run_id, claim_id):
    return client.post(f"/api/runs/{run_id}/claims/{claim_id}")


def fail(client, claim_id, reason="The agent failed: timed out"):
    body = {"thread_id": "t1", "reason": reason}
    return client.post(f"/api/claims/{claim_id}/return", json=body)


def to_work(client, run_id):
    found = client.get(f"/api/runs/{run_id}/claims-to-work").json()
    return [c["claim_id"] for c in found]


def stop(client, run_id, reason="Stopped by hand."):
    return client.post(f"/api/runs/{run_id}/stop", json={"reason": reason})


def test_a_dispatch_records_its_settings(client, run_id):
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["run_id"] == "RUN-0001"
    assert (run["kind"], run["agents"], run["claim_set"], run["tiny"]) == (
        "dispatch",
        3,
        "queue",
        False,
    )
    assert (run["model"], run["reasoning_effort"]) == ("openai/gpt-6-luna", "low")
    assert (run["status"], run["reason"], run["cost"]) == ("running", None, 0.0)
    assert client.get("/api/dispatches/latest").json()["run_id"] == run_id


def test_the_claims_to_work_are_in_progress_first_then_oldest_submitted(client, run_id):
    queue = client.get("/api/claims").json()
    oldest = [c["claim_id"] for c in sorted(queue, key=lambda c: c["submitted_on"])]
    assert to_work(client, run_id) == oldest
    take(client, run_id, oldest[-1])
    stop(client, run_id)
    later = client.post("/api/dispatches", json=DISPATCH).json()["run_id"]
    assert to_work(client, later) == [oldest[-1], *oldest[:-1]]


def test_a_claim_in_progress_carries_on_in_the_next_dispatch(client, run_id):
    first = take(client, run_id, "CLM-1001").json()
    assert (first["status"], first["run_id"]) == ("in_progress", run_id)
    stopped = stop(client, run_id).json()
    assert (stopped["status"], stopped["reason"]) == ("stopped", "Stopped by hand.")
    assert status(client, "CLM-1001") == "in_progress"

    later = client.post("/api/dispatches", json=DISPATCH).json()["run_id"]
    again = take(client, later, "CLM-1001").json()
    assert again["thread_id"] == first["thread_id"]
    assert (again["run_id"], again["attempts"]) == (later, 0)


def test_a_failed_claim_goes_back_in_the_queue(client, run_id):
    take(client, run_id, "CLM-1001")
    returned = fail(client, "CLM-1001").json()
    assert (returned["status"], returned["attempts"]) == ("waiting", 1)
    assert returned["thread_id"] is None
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert steps[-1]["text"] == (
        "The agent failed: timed out\nBack in the queue after attempt 1."
    )
    again = take(client, run_id, "CLM-1001").json()["thread_id"]
    assert again


def test_a_claim_that_fails_twice_is_left_for_a_handler(client, run_id):
    take(client, run_id, "CLM-1001")
    fail(client, "CLM-1001")
    take(client, run_id, "CLM-1001")
    returned = fail(client, "CLM-1001").json()
    assert (returned["status"], returned["attempts"]) == ("needs_handler", 2)
    assert "CLM-1001" not in to_work(client, run_id)
    assert take(client, run_id, "CLM-1001").status_code == 409


def test_a_claim_is_never_worked_twice(client, run_id):
    take(client, run_id, "CLM-1001")
    decide(client, "CLM-1001", "decline", 0.0)
    take(client, run_id, "CLM-1003")
    decide(client, "CLM-1003", "approve", 3750.0)
    for claim_id in ("CLM-1001", "CLM-1003"):
        assert fail(client, claim_id).status_code == 409
        refused = take(client, run_id, claim_id)
        assert (
            refused.json()["detail"] == f"{claim_id} is not a claim this run can work"
        )
    assert status(client, "CLM-1001") == "decided"
    assert status(client, "CLM-1003") == "awaiting_sign_off"
    assert fail(client, "CLM-1002").status_code == 409


def test_a_run_finishes_once_none_of_its_claims_is_waiting(client, run_id):
    take(client, run_id, "CLM-1001")
    fail(client, "CLM-1001")
    refused = client.post(f"/api/runs/{run_id}/finish")
    assert refused.json()["detail"] == "Still waiting: CLM-1001"
    take(client, run_id, "CLM-1001")
    finished = client.post(f"/api/runs/{run_id}/finish").json()
    assert finished["status"] == "finished"
    assert finished["summary"]["in_progress"] == ["CLM-1001"]
    assert finished["finished_at"]
    assert client.post(f"/api/runs/{run_id}/finish").status_code == 409
    assert stop(client, run_id).status_code == 409


def test_one_run_at_a_time(client, run_id):
    refused = client.post("/api/dispatches", json=DISPATCH)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "A dispatch or evaluation is already running"


def test_no_run_yet(client):
    assert client.get("/api/dispatches/latest").json() is None
    assert client.get("/api/runs/latest").json() is None
    assert client.get("/api/runs/RUN-9999").status_code == 404


def test_a_backend_restart_leaves_the_agent_s_work_alone(client, run_id):
    take(client, run_id, "CLM-1001")
    with TestClient(app):
        pass
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "running"
    claim = client.get("/api/claims/CLM-1001").json()
    assert (claim["status"], claim["attempts"]) == ("in_progress", 0)


def test_a_dispatch_is_handed_to_the_agent(client, agent_calls):
    response = client.post("/api/dispatches/start", json={"agents": 3})
    assert response.status_code == 202
    assert agent_calls == [("/dispatches", {"agents": 3})]
    for agents in (0, 26):
        refused = client.post("/api/dispatches/start", json={"agents": agents})
        assert refused.status_code == 422


def test_one_claim_is_handed_to_the_agent(client, agent_calls):
    assert client.post("/api/claims/CLM-1001/agent").status_code == 202
    assert agent_calls == [("/claims/CLM-1001/work", None)]
    decide(client, "CLM-1002", "decline", 0.0)
    refused = client.post("/api/claims/CLM-1002/agent")
    assert refused.json()["detail"] == "CLM-1002 is not waiting"
    assert len(agent_calls) == 1


def answer(monkeypatch, handler):
    """Answer the backend's calls to the agent's service with a handler."""
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(agent_service, "post", REAL_POST)
    monkeypatch.setattr(
        agent_service,
        "agent",
        lambda: httpx.Client(base_url="http://agent", transport=transport),
    )


def test_a_refusal_from_the_agent_is_passed_on(client, monkeypatch):
    busy = {"detail": "A dispatch or evaluation is already running"}
    answer(monkeypatch, lambda request: httpx.Response(409, json=busy))
    refused = client.post("/api/dispatches/start", json={"agents": 3})
    assert (refused.status_code, refused.json()) == (409, busy)


def test_an_agent_that_is_not_running(client, monkeypatch):
    def unreachable(request):
        raise httpx.ConnectError("refused", request=request)

    answer(monkeypatch, unreachable)
    refused = client.post("/api/dispatches/start", json={"agents": 3})
    assert refused.status_code == 409
    assert refused.json()["detail"] == "The agent's service is not running"
    decide(client, "CLM-1003", "approve", 3750.0)
    signed = client.post("/api/claims/CLM-1003/sign-off", json={"handler_id": "HND-03"})
    assert signed.status_code == 200
