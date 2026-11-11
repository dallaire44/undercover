from backend import runner
from backend.tests.conftest import decide, status


def start(client, cap=2):
    return client.post("/api/runs", json={"cap": cap})


def run_of(client, run_id):
    return client.get(f"/api/runs/{run_id}").json()


def test_a_run_with_the_agent_off_waits(client, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_AGENT", "off")
    response = start(client)
    assert response.status_code == 202
    run = response.json()
    assert run["run_id"] == "RUN-0001"
    assert run["cap"] == 2
    assert run["status"] == "running"
    assert client.get("/api/runs/latest").json()["run_id"] == "RUN-0001"


def test_a_failing_queue_agent_returns_its_claims(client, monkeypatch):
    def run_queue(run_id):
        client.post(f"/api/runs/{run_id}/claims/CLM-1001")
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(runner.queue, "run_queue", run_queue)
    run = run_of(client, start(client).json()["run_id"])
    assert run["status"] == "stopped"
    assert run["summary"] == "The agent failed: provider unavailable"
    assert status(client, "CLM-1001") == "waiting"


def test_a_finished_run_is_left_alone(client, monkeypatch):
    def run_queue(run_id):
        client.post(f"/api/runs/{run_id}/claims/CLM-1001")
        decide(client, "CLM-1001", "decline", 0.0)
        client.post(f"/api/runs/{run_id}/finish", json={"summary": "One declined."})

    monkeypatch.setattr(runner.queue, "run_queue", run_queue)
    run = run_of(client, start(client, 1).json()["run_id"])
    assert run["status"] == "finished"
    assert run["summary"] == "One declined."


def test_one_claim(client, monkeypatch):
    def work_claim(run_id, claim_id):
        client.post(f"/api/runs/{run_id}/claims/{claim_id}")
        decide(client, claim_id, "refer", 0.0)
        return f"{claim_id}: referred"

    monkeypatch.setattr(runner.queue, "work_claim", work_claim)
    response = client.post("/api/claims/CLM-1001/agent")
    assert response.status_code == 202
    run = run_of(client, response.json()["run_id"])
    assert run["summary"] == "CLM-1001: referred"
    assert run["claim_ids"] == ["CLM-1001"]


def test_one_claim_must_be_waiting(client, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_AGENT", "off")
    decide(client, "CLM-1001", "decline", 0.0)
    assert client.post("/api/claims/CLM-1001/agent").status_code == 409
    assert client.post("/api/claims/CLM-9999/agent").status_code == 404
    assert client.get("/api/runs/latest").json() is None
