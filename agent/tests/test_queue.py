from contextlib import closing

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from agent import claim, cli, model, queue
from agent.tests.conftest import Recorder, call, decide, stub
from backend import db, runner, runs


@pytest.fixture
def start(client, monkeypatch):
    """Start runs without starting the agent, so each test drives it."""
    monkeypatch.setenv("UNDERCOVER_AGENT", "off")

    def start(cap):
        return client.post("/api/runs", json={"cap": cap}).json()["run_id"]

    return start


@pytest.fixture
def claim_agent(client, monkeypatch):
    """A fake claim agent that declines, and fails on the claims in `failing`."""
    failing: dict[str, int] = {}

    def run(claim_id, thread_id):
        if failing.get(claim_id):
            failing[claim_id] -= 1
            raise RuntimeError("timed out")
        decide(client, claim_id)
        return "Declined."

    monkeypatch.setattr(claim, "run", run)
    return failing


def work(*claim_ids):
    return [call("work_claim", claim_id=claim_id) for claim_id in claim_ids]


def finish():
    return [call("finish_run", summary="Done."), AIMessage(content="Finished.")]


def status(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def run_of(client, run_id):
    return client.get(f"/api/runs/{run_id}").json()


def test_a_failed_claim_does_not_stop_the_run(client, start, claim_agent):
    claim_agent["CLM-1002"] = 2
    run_id = start(3)
    replies = [*work("CLM-1001", "CLM-1002", "CLM-1003", "CLM-1002"), *finish()]
    queue.run_queue(run_id, stub(*replies))
    assert status(client, "CLM-1001") == "decided"
    assert status(client, "CLM-1003") == "decided"
    assert status(client, "CLM-1002") == "needs_handler"
    assert run_of(client, run_id)["status"] == "finished"


def test_a_failed_claim_is_tried_again(client, start, claim_agent):
    claim_agent["CLM-1002"] = 1
    run_id = start(2)
    replies = [*work("CLM-1001", "CLM-1002", "CLM-1002"), *finish()]
    queue.run_queue(run_id, stub(*replies))
    record = client.get("/api/claims/CLM-1002").json()
    assert record["status"] == "decided"
    assert record["attempts"] == 1
    assert run_of(client, run_id)["status"] == "finished"


def test_work_claim_reports_in_one_line(client, start, claim_agent):
    claim_agent["CLM-1002"] = 2
    run_id = start(2)
    assert queue.work_claim(run_id, "CLM-1001") == "CLM-1001: declined"
    assert queue.work_claim(run_id, "CLM-1002") == (
        "CLM-1002: failed, back in the queue to try again. The agent failed: timed out"
    )
    assert queue.work_claim(run_id, "CLM-1002").startswith(
        "CLM-1002: failed twice, left for a handler."
    )
    assert queue.work_claim(run_id, "CLM-1003") == (
        "CLM-1003: not taken. The run's cap of 2 claims is reached"
    )


def test_work_claim_reports_payments(client, start, monkeypatch):
    def approve(claim_id, thread_id):
        decide(client, claim_id, "approve", 420.0 if claim_id == "CLM-1001" else 3750.0)
        if claim_id == "CLM-1001":
            client.post(f"/api/claims/{claim_id}/payment", json={"amount": 420.0})

    monkeypatch.setattr(claim, "run", approve)
    run_id = start(3)
    assert queue.work_claim(run_id, "CLM-1001") == "CLM-1001: approved, $420.00 paid"
    assert queue.work_claim(run_id, "CLM-1003") == (
        "CLM-1003: approved, $3,750.00 waiting for sign-off"
    )


def test_an_approval_left_unpaid_goes_back_in_the_queue(client, start, monkeypatch):
    monkeypatch.setattr(
        claim, "run", lambda claim_id, _: decide(client, claim_id, "approve", 420.0)
    )
    run_id = start(1)
    line = queue.work_claim(run_id, "CLM-1001")
    assert line == (
        "CLM-1001: failed, back in the queue to try again. "
        "The agent finished without completing the claim."
    )
    assert status(client, "CLM-1001") == "waiting"


def test_the_cap_on_a_run(client, start, claim_agent):
    run_id = start(2)
    replies = [*work("CLM-1001", "CLM-1002", "CLM-1003"), *finish()]
    queue.run_queue(run_id, stub(*replies))
    assert run_of(client, run_id)["claim_ids"] == ["CLM-1001", "CLM-1002"]
    claims = client.get("/api/claims").json()
    assert [c["status"] for c in claims].count("waiting") == 23
    assert run_of(client, run_id)["status"] == "finished"


def test_the_check_for_missed_claims(client, start, claim_agent):
    run_id = start(2)
    model_ = Recorder(
        messages=iter([*work("CLM-1001"), *finish()[:1], *work("CLM-1002"), *finish()])
    )
    queue.run_queue(run_id, model_)
    refusal = model_.seen[2][-1]
    assert isinstance(refusal, ToolMessage)
    assert refusal.text.startswith("Refused (409): Still to work within the cap:")
    assert status(client, "CLM-1002") == "decided"
    assert run_of(client, run_id)["status"] == "finished"


def test_the_to_do_list_and_the_claims_to_work(client, start):
    run_id = start(2)
    todos = [
        {"content": "CLM-1001: baggage, $385.00", "status": "in_progress"},
        {"content": "Check for missed claims", "status": "to_do"},
    ]
    model_ = Recorder(
        messages=iter(
            [
                call("list_claims_to_work"),
                call("write_todos", todos=todos),
                AIMessage(content="Paused."),
            ]
        )
    )
    assert queue.run_queue(run_id, model_) == "Paused."
    header, *listed = model_.seen[1][-1].text.splitlines()
    assert header.startswith(
        "The run's cap is 2 claims. It has taken 0, so it can take 2"
    )
    assert len(listed) == 25
    assert listed[0].startswith("CLM-1001: trip delay, $420.00, submitted 2026-06-24")
    assert "0 earlier attempts" in listed[0]
    assert run_of(client, run_id)["todos"] == todos


def test_a_fresh_start_for_each_claim(client, start, monkeypatch):
    calls = []

    def fresh():
        recorder = Recorder(messages=iter([AIMessage(content="Not sure.")]))
        calls.append(recorder)
        return recorder

    monkeypatch.setattr(claim, "model", fresh)
    run_id = start(2)
    queue.run_queue(run_id, stub(*work("CLM-1001", "CLM-1002"), AIMessage("Stop.")))
    for claim_id, recorder in zip(["CLM-1001", "CLM-1002"], calls, strict=True):
        first = recorder.seen[0]
        assert len(first) == 2
        assert first[1].text == f"Decide claim {claim_id}."
    threads = [
        {s["thread_id"] for s in client.get(f"/api/claims/{c}/steps").json()}
        for c in ("CLM-1001", "CLM-1002")
    ]
    assert len(threads[0]) == len(threads[1]) == 1
    assert threads[0] != threads[1]


def test_a_run_that_ends_without_finishing_is_stopped(client, start, monkeypatch):
    run_id = start(2)
    monkeypatch.setattr(queue, "model", lambda: stub(AIMessage(content="Bye.")))
    runner.run_queue(run_id)
    run = run_of(client, run_id)
    assert run["status"] == "stopped"
    assert run["summary"] == "The agent ended without finishing the run."


def test_a_failing_queue_agent_is_retried_then_stops_the_run(
    client, start, monkeypatch
):
    monkeypatch.setattr(model, "RETRY_DELAY_SECONDS", 0.001)

    class Broken(Recorder):
        def _generate(self, messages, *args, **kwargs):
            self.seen.append(messages)
            raise ConnectionError("provider unavailable")

    broken = Broken(messages=iter([]))
    monkeypatch.setattr(queue, "model", lambda: broken)
    run_id = start(2)
    runner.run_queue(run_id)
    assert len(broken.seen) == 1 + model.QUEUE_RETRIES
    run = run_of(client, run_id)
    assert run["status"] == "stopped"
    assert run["summary"] == "The agent failed: provider unavailable"


def test_one_named_claim(client, claim_agent):
    response = client.post("/api/claims/CLM-1001/agent")
    assert response.status_code == 202
    run = run_of(client, response.json()["run_id"])
    assert run["cap"] == 1
    assert run["status"] == "finished"
    assert run["summary"] == "CLM-1001: declined"
    assert client.post("/api/claims/CLM-1001/agent").status_code == 409


def test_a_queue_run_from_the_api(client, monkeypatch):
    monkeypatch.setattr(queue, "model", lambda: stub(*finish()))
    run = client.post("/api/runs", json={"cap": 0})
    assert run.status_code == 422
    response = client.post("/api/runs", json={"cap": 1})
    assert response.status_code == 202
    assert run_of(client, response.json()["run_id"])["status"] == "stopped"


def test_one_run_at_a_time(client, start):
    start(5)
    assert client.post("/api/claims/CLM-1002/agent").status_code == 409
    assert client.post("/api/runs", json={"cap": 1}).status_code == 409


def test_the_command_line(client, claim_agent):
    run_id = cli.start("CLM-1001")
    assert cli.follow(run_id) == f"{run_id} finished: CLM-1001: declined"


def test_the_command_line_follows_the_to_do_list(client, start, monkeypatch, capsys):
    run_id = cli.start("3")
    todo = {"content": "CLM-1001", "status": "to_do"}
    client.put(f"/api/runs/{run_id}/todos", json={"todos": [todo]})

    def stop(seconds):
        with closing(db.connect()) as conn:
            runs.stop(conn, run_id, "Stopped by hand.")

    monkeypatch.setattr(cli.time, "sleep", stop)
    assert cli.follow(run_id) == f"{run_id} stopped: Stopped by hand."
    assert "[to_do] CLM-1001" in capsys.readouterr().out


def test_no_claims_left_to_work(client, start, claim_agent):
    run_id = start(1)
    queue.work_claim(run_id, "CLM-1001")
    model_ = Recorder(messages=iter([call("list_claims_to_work"), AIMessage("Done.")]))
    queue.run_queue(run_id, model_)
    assert model_.seen[1][-1].text == "No claims left to work."
