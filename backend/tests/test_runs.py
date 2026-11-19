from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from backend import db, runs
from backend.errors import Refused
from backend.main import app
from backend.tests.conftest import decide, status


@pytest.fixture
def run_id(client):
    """A running run capped at two claims."""
    with closing(db.connect()) as conn:
        return runs.start(conn, 2).run_id


def take(client, run_id, claim_id):
    return client.post(f"/api/runs/{run_id}/claims/{claim_id}")


def fail(client, claim_id, reason="The agent failed: timed out"):
    body = {"thread_id": "t1", "reason": reason}
    return client.post(f"/api/claims/{claim_id}/return", json=body)


def to_work(client, run_id):
    found = client.get(f"/api/runs/{run_id}/claims-to-work").json()
    return [c["claim_id"] for c in found]


def finish(client, run_id):
    body = {"summary": "Two claims worked."}
    return client.post(f"/api/runs/{run_id}/finish", json=body)


def test_the_cap(client, run_id):
    assert len(to_work(client, run_id)) == 25
    assert take(client, run_id, "CLM-1001").json()["status"] == "in_progress"
    assert take(client, run_id, "CLM-1002").status_code == 200
    refused = take(client, run_id, "CLM-1003")
    assert refused.status_code == 409
    assert refused.json()["detail"] == "The run's cap of 2 claims is reached"
    assert to_work(client, run_id) == []
    assert status(client, "CLM-1003") == "waiting"
    assert client.get(f"/api/runs/{run_id}").json()["claim_ids"] == [
        "CLM-1001",
        "CLM-1002",
    ]


def test_a_failed_claim_goes_back_in_the_queue(client, run_id):
    take(client, run_id, "CLM-1001")
    take(client, run_id, "CLM-1002")
    returned = fail(client, "CLM-1001").json()
    assert returned["status"] == "waiting"
    assert returned["attempts"] == 1
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert steps[-1]["text"] == (
        "The agent failed: timed out\nBack in the queue after attempt 1."
    )
    assert to_work(client, run_id) == ["CLM-1001"]
    assert take(client, run_id, "CLM-1001").status_code == 200


def test_a_claim_that_fails_twice_is_left_for_a_handler(client, run_id):
    take(client, run_id, "CLM-1001")
    fail(client, "CLM-1001")
    take(client, run_id, "CLM-1001")
    returned = fail(client, "CLM-1001").json()
    assert returned["status"] == "needs_handler"
    assert returned["attempts"] == 2
    assert "CLM-1001" not in to_work(client, run_id)
    assert take(client, run_id, "CLM-1001").status_code == 409


def test_a_claim_is_never_worked_twice(client, run_id):
    take(client, run_id, "CLM-1001")
    decide(client, "CLM-1001", "decline", 0.0)
    take(client, run_id, "CLM-1003")
    decide(client, "CLM-1003", "approve", 3750.0)
    for claim_id in ("CLM-1001", "CLM-1003"):
        assert fail(client, claim_id).status_code == 409
        assert take(client, run_id, claim_id).status_code == 409
    assert status(client, "CLM-1001") == "decided"
    assert status(client, "CLM-1003") == "awaiting_sign_off"
    assert fail(client, "CLM-1002").status_code == 409


def test_the_check_for_missed_claims(client, run_id):
    take(client, run_id, "CLM-1001")
    refused = finish(client, run_id)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "Still in progress: CLM-1001"
    decide(client, "CLM-1001", "decline", 0.0)
    take(client, run_id, "CLM-1002")
    fail(client, "CLM-1002")
    refused = finish(client, run_id)
    assert refused.json()["detail"] == "Still to work within the cap: CLM-1002"
    take(client, run_id, "CLM-1002")
    decide(client, "CLM-1002", "refer", 0.0)
    finished = finish(client, run_id).json()
    assert finished["status"] == "finished"
    assert finished["summary"] == "Two claims worked."
    assert finished["finished_at"]
    assert finish(client, run_id).status_code == 409


def test_the_to_do_list(client, run_id):
    assert client.get("/api/runs/latest").json()["todos"] == []
    todos = [
        {"content": "Work CLM-1002", "status": "in_progress"},
        {"content": "Work CLM-1001", "status": "to_do"},
        {"content": "Check for missed claims", "status": "to_do"},
    ]
    response = client.put(f"/api/runs/{run_id}/todos", json={"todos": todos})
    assert response.json() == todos
    todos[0]["status"] = "done"
    client.put(f"/api/runs/{run_id}/todos", json={"todos": todos[:2]})
    assert client.get("/api/runs/latest").json()["todos"] == todos[:2]
    bad = [{"content": "Work CLM-1001", "status": "maybe"}]
    response = client.put(f"/api/runs/{run_id}/todos", json={"todos": bad})
    assert response.status_code == 422


def test_one_run_at_a_time(client, run_id):
    with closing(db.connect()) as conn, pytest.raises(Refused, match="already"):
        runs.start(conn, 5)


def test_no_run_yet(client):
    assert client.get("/api/runs/latest").json() is None
    assert client.get("/api/runs/RUN-9999").status_code == 404


def test_a_backend_restart_leaves_the_agent_s_work_alone(client, run_id):
    take(client, run_id, "CLM-1001")
    with TestClient(app):
        pass
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "running"
    claim = client.get("/api/claims/CLM-1001").json()
    assert (claim["status"], claim["attempts"]) == ("in_progress", 0)


def test_the_agent_stops_a_run_it_cannot_finish(client, run_id):
    take(client, run_id, "CLM-1001")
    body = {"reason": "The agent failed: provider unavailable"}
    run = client.post(f"/api/runs/{run_id}/stop", json=body).json()
    assert (run["status"], run["summary"]) == ("stopped", body["reason"])
    assert status(client, "CLM-1001") == "waiting"
    assert client.post(f"/api/runs/{run_id}/stop", json=body).status_code == 409


def test_each_attempt_has_its_own_thread(client, run_id):
    first = take(client, run_id, "CLM-1001").json()
    assert first["thread_id"]
    assert first["run_id"] == run_id
    assert fail(client, "CLM-1001").json()["thread_id"] is None
    again = take(client, run_id, "CLM-1001").json()["thread_id"]
    assert again
    assert again != first["thread_id"]
