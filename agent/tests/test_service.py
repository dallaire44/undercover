from fastapi.testclient import TestClient

from agent import dispatcher, harness, service
from agent.tests.conftest import Recorder, call, decide, dispatch_id, stub
from backend.tests.test_openapi import assert_every_operation_follows_the_rules

agent_service = TestClient(service.app)


def approve(claim_id, payout):
    return call(
        "record_decision",
        claim_id=claim_id,
        decision="approve",
        payout=payout,
        reason="The wording covers it.",
        policy_section="4. Emergency Medical",
    )


def test_every_operation_follows_the_rules():
    assert_every_operation_follows_the_rules(service.app)
    assert agent_service.get("/health").json() == {"status": "ok"}


def test_one_run_at_a_time(client, monkeypatch):
    dispatched = []
    monkeypatch.setattr(dispatcher, "dispatch", lambda *args: dispatched.append(args))
    assert agent_service.post("/dispatches", json={"agents": 3}).status_code == 202
    run = client.get("/api/dispatches/latest").json()
    assert (run["agents"], run["model"], run["reasoning_effort"]) == (
        3,
        "openai/gpt-6-luna",
        "low",
    )
    assert dispatched == [(run["run_id"], 3, service.RESUMING, None)]

    with service.RUN_LOCK:
        refused = agent_service.post("/dispatches", json={"agents": 3})
        assert (refused.status_code, refused.json()["detail"]) == (409, service.BUSY)
        assert agent_service.post("/claims/CLM-1001/work").status_code == 409
    client.post(f"/api/runs/{run['run_id']}/finish")
    assert agent_service.post("/claims/CLM-1001/work").status_code == 202
    assert dispatched[-1][1:] == (1, service.RESUMING, "CLM-1001")
    assert agent_service.post("/dispatches", json={"agents": 26}).status_code == 422


def test_one_claim_in_a_dispatch_of_its_own(client, script):
    assert agent_service.post("/claims/CLM-1001/work").status_code == 202
    run = client.get("/api/dispatches/latest").json()
    assert (run["agents"], run["status"]) == (1, "finished")
    assert [c["claim_id"] for c in run["claims"]] == ["CLM-1001"]
    assert [claim_id for claim_id, _ in script.calls] == ["CLM-1001"] * 3


def test_a_dispatch_started_on_the_backend(client, service, script):
    left = ["CLM-1002", "CLM-1005", "CLM-1009"]
    for claim in client.get("/api/claims").json():
        if claim["claim_id"] not in left:
            decide(client, claim["claim_id"])
    assert client.post("/api/dispatches/start", json={"agents": 3}).status_code == 202
    run = client.get("/api/dispatches/latest").json()
    assert run["status"] == "finished"
    assert [c["claim_id"] for c in run["claims"]] == left
    assert run["summary"]["declined"] == 3
    assert run["cost"] > 0
    assert run["seconds"] >= 0
    assert all(c["seconds"] > 0 for c in run["claims"])


def test_on_start_the_run_left_running_is_stopped(client, monkeypatch):
    stopped = []
    monkeypatch.setattr(harness, "set_up_checkpoints", lambda: stopped.append("set"))
    monkeypatch.setattr(service, "stop_left_running", lambda: stopped.append("stop"))
    with TestClient(service.app):
        pass
    assert stopped == ["set", "stop"]


def test_the_run_left_running_is_stopped_and_its_claims_stay(client):
    service.stop_left_running()
    run_id = dispatch_id(client)
    client.post(f"/api/runs/{run_id}/claims/CLM-1001")
    service.stop_left_running()
    run = client.get(f"/api/runs/{run_id}").json()
    assert (run["status"], run["reason"]) == ("stopped", service.RESTARTED)
    assert run["summary"]["in_progress"] == ["CLM-1001"]
    service.stop_left_running()


def test_a_claim_being_resumed_is_left_out_of_dispatches(monkeypatch):
    during = []
    monkeypatch.setattr(
        harness, "resume", lambda claim_id: during.append(set(service.RESUMING))
    )
    assert agent_service.post("/claims/CLM-1003/resume").status_code == 202
    assert during == [{"CLM-1003"}]
    assert not service.RESUMING


def test_a_sign_off_on_the_backend_resumes_the_claim_and_pays_it_once(
    client, service, monkeypatch
):
    monkeypatch.setattr(harness, "model", lambda: stub(approve("CLM-1003", 3750.0)))
    run_id = dispatch_id(client)
    line = harness.work_claim(run_id, "CLM-1003")
    assert line == "CLM-1003: approved, $3,750.00 waiting for sign-off"

    idle = Recorder(messages=iter([]))
    idle.seen.clear()
    monkeypatch.setattr(harness, "model", lambda: idle)
    client.post("/api/claims/CLM-1003/sign-off", json={"handler_id": "HND-03"})
    record = client.get("/api/claims/CLM-1003").json()
    assert record["status"] == "decided"
    assert record["payment"]["amount"] == 3750.0
    assert record["payment"]["signed_off_by"] == "Priya Raman"
    assert idle.seen == []
    harness.resume("CLM-1003")
    paid = client.get("/api/claims/CLM-1003").json()["payment"]
    assert paid == record["payment"]
