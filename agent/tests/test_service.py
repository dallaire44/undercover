import pytest
from fastapi.testclient import TestClient

from agent import harness, service
from agent.tests.conftest import Recorder, StopsOnce, call, stub
from backend import db, runs
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


def test_each_operation_answers_at_once_and_works_in_the_background(monkeypatch):
    done = []
    monkeypatch.setattr(harness, "work_run", lambda *args: done.append(args))
    monkeypatch.setattr(harness, "work_one", lambda *args: done.append(args))
    monkeypatch.setattr(harness, "resume", lambda *args: done.append(args))
    assert agent_service.post("/runs/RUN-0001").status_code == 202
    assert agent_service.post("/runs/RUN-0001/claims/CLM-1001").status_code == 202
    assert agent_service.post("/claims/CLM-1003/resume").status_code == 202
    assert done == [("RUN-0001",), ("RUN-0001", "CLM-1001"), ("CLM-1003",)]
    assert agent_service.get("/health").json() == {"status": "ok"}


def test_a_run_first_carries_on(client, monkeypatch):
    order = []
    monkeypatch.setattr(harness, "carry_on", lambda: order.append("carry on"))
    monkeypatch.setattr(harness, "run_queue", order.append)
    run_id = client.post("/api/runs", json={"cap": 1}).json()["run_id"]
    harness.work_run(run_id)
    assert order == ["carry on", run_id]


def test_a_sign_off_on_the_backend_resumes_the_claim_and_pays_it_once(
    client, service, monkeypatch
):
    monkeypatch.setattr(harness, "model", lambda: stub(approve("CLM-1003", 3750.0)))
    with db.connect() as conn:
        run_id = runs.start(conn, 1).run_id
    line = harness.work_claim(run_id, "CLM-1003")
    assert line == "CLM-1003: approved, $3,750.00 waiting for sign-off"

    idle = Recorder(messages=iter([]))
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


def test_one_claim_is_tried_again_once_if_it_fails(client, monkeypatch):
    class Broken(Recorder):
        def _generate(self, messages, *args, **kwargs):
            raise RuntimeError("the model broke")

    decline = call(
        "record_decision",
        claim_id="CLM-1001",
        decision="decline",
        payout=0.0,
        reason="Excluded.",
        policy_section="9. General exclusions",
    )
    models = iter([Broken(messages=iter([])), stub(decline)])
    monkeypatch.setattr(harness, "model", lambda: next(models))
    run_id = client.post("/api/claims/CLM-1001/agent").json()["run_id"]
    harness.work_one(run_id, "CLM-1001")
    run = client.get(f"/api/runs/{run_id}").json()
    assert (run["status"], run["summary"]) == ("finished", "CLM-1001: declined")
    assert client.get("/api/claims/CLM-1001").json()["attempts"] == 1


def test_on_start_the_agent_carries_on_a_run_left_running(client, monkeypatch):
    done = []
    monkeypatch.setattr(harness, "work_run", done.append)
    monkeypatch.setattr(harness, "carry_on", lambda: done.append("carry on"))
    harness.pick_up()
    assert done == ["carry on"]
    run_id = client.post("/api/runs", json={"cap": 1}).json()["run_id"]
    harness.pick_up()
    assert done == ["carry on", run_id]


def test_the_service_sets_up_and_picks_up_when_it_starts(monkeypatch):
    started = []
    monkeypatch.setattr(harness, "pick_up", lambda: started.append("pick up"))
    with TestClient(service.app):
        pass
    assert started == ["pick up"]


def test_on_start_a_run_on_one_claim_stopped_partway_is_finished(client, monkeypatch):
    model_ = StopsOnce(
        stop_at=1,
        messages=iter(
            [call("get_claim", claim_id="CLM-1001"), approve("CLM-1001", 420.0)]
        ),
    )
    monkeypatch.setattr(harness, "model", lambda: model_)
    with db.connect() as conn:
        run_id = runs.start(conn, 1).run_id
    with pytest.raises(KeyboardInterrupt):
        harness.work_one(run_id, "CLM-1001")
    assert not harness.has_queue_thread(run_id)

    harness.pick_up()
    run = client.get(f"/api/runs/{run_id}").json()
    assert (run["status"], run["summary"]) == (
        "finished",
        "CLM-1001: approved, $420.00 paid",
    )
    assert harness.has_queue_thread(run_id) is False
