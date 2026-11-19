import threading
import time

import pytest
from langchain_core.exceptions import ModelRateLimitError, ModelTimeoutError
from langchain_core.messages import ToolMessage

from agent import api, dispatcher, harness
from agent.tests.conftest import all_but, dispatch_id

TEN = [f"CLM-{n}" for n in range(1001, 1011)]


def claim(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()


def run_of(client, run_id):
    return client.get(f"/api/runs/{run_id}").json()


def threads(client, claim_id):
    found = client.get(f"/api/claims/{claim_id}/steps").json()
    return list(dict.fromkeys(s["thread_id"] for s in found))


def decision_calls(client, claim_id):
    found = client.get(f"/api/claims/{claim_id}/steps").json()
    return [s for s in found if s["text"].startswith("record_decision(")]


def dispatch(client, run_id, agents, *claim_ids):
    return dispatcher.dispatch(run_id, agents, all_but(client, *claim_ids), None)


@pytest.fixture
def stand_in(monkeypatch):
    """A stand-in for the claim agent that records how many work at once."""
    worked: list[str] = []
    most = [0]
    running = [0]
    lock = threading.Lock()

    def work_claim(run_id, claim_id):
        with lock:
            running[0] += 1
            most[0] = max(most[0], running[0])
        time.sleep(0.1)
        with lock:
            running[0] -= 1
            worked.append(claim_id)
        return f"{claim_id}: worked"

    monkeypatch.setattr(harness, "work_claim", work_claim)
    return worked, most


def test_never_more_than_n_at_once(client, stand_in):
    worked, most = stand_in
    run_id = dispatch_id(client, 3)
    lines = dispatch(client, run_id, 3, *TEN)
    assert most == [3]
    assert sorted(worked) == TEN
    assert len(lines) == 10
    assert run_of(client, run_id)["status"] == "finished"


def test_one_at_a_time_the_oldest_submitted_first(client, stand_in):
    worked, most = stand_in
    queue = client.get("/api/claims").json()
    oldest_first = [
        c["claim_id"]
        for c in sorted(queue, key=lambda c: (c["submitted_on"], c["claim_id"]))
        if c["claim_id"] in TEN
    ]
    dispatch(client, dispatch_id(client, 1), 1, *TEN)
    assert most == [1]
    assert worked == oldest_first


def test_a_dispatch_carries_on_what_a_stopped_one_left(client, script):
    script.errors["CLM-1003"] = [None, KeyboardInterrupt()]
    first = dispatch_id(client)
    with pytest.raises(KeyboardInterrupt):
        harness.work_claim(first, "CLM-1003")
    client.post(f"/api/runs/{first}/stop", json={"reason": "Stopped by hand."})
    left = claim(client, "CLM-1003")
    assert left["status"] == "in_progress"

    second = dispatch_id(client, 1)
    dispatch(client, second, 1, "CLM-1001", "CLM-1002", "CLM-1003")
    record = claim(client, "CLM-1003")
    assert (record["status"], record["attempts"]) == ("decided", 0)
    assert record["thread_id"] == left["thread_id"]
    assert record["run_id"] == second
    carried_on = [c for c, _ in script.calls[2:]]
    assert carried_on[0] == "CLM-1003"
    run = run_of(client, second)
    assert run["status"] == "finished"
    assert {c["status"] for c in run["claims"]} == {"decided"}


def test_a_rate_limit_carries_on_as_the_same_attempt(client, script):
    limit = ModelRateLimitError("rate limited")
    script.errors["CLM-1001"] = [None, None, limit, limit, limit]
    run_id = dispatch_id(client)
    assert dispatch(client, run_id, 3, "CLM-1001") == ["CLM-1001: declined"]
    record = claim(client, "CLM-1001")
    assert (record["status"], record["attempts"]) == ("decided", 0)
    assert len(threads(client, "CLM-1001")) == 1
    assert len(decision_calls(client, "CLM-1001")) == 1
    assert len(script.calls) == 6
    _, carried_on = script.calls[-1]
    tools = [m.name for m in carried_on if isinstance(m, ToolMessage)]
    assert tools == ["get_claim", "list_sections"]


def test_retries_run_out_without_stopping_the_dispatch(client, script):
    script.errors["CLM-1001"] = [ModelTimeoutError("timed out")] * 9
    run_id = dispatch_id(client)
    lines = dispatch(client, run_id, 3, "CLM-1001", "CLM-1002", "CLM-1004")
    assert "CLM-1001: still in progress, for the next dispatch" in lines
    record = claim(client, "CLM-1001")
    assert (record["status"], record["attempts"]) == ("in_progress", 0)
    assert record["thread_id"] is not None
    assert claim(client, "CLM-1002")["status"] == "decided"
    assert claim(client, "CLM-1004")["status"] == "decided"
    run = run_of(client, run_id)
    assert run["status"] == "finished"
    assert run["summary"]["in_progress"] == ["CLM-1001"]


def test_a_failure_is_tried_once_more_in_the_same_dispatch(client, script):
    script.errors["CLM-1001"] = [RuntimeError("the model broke")]
    script.errors["CLM-1002"] = [RuntimeError("the model broke")] * 2
    run_id = dispatch_id(client)
    dispatch(client, run_id, 3, "CLM-1001", "CLM-1002")
    record = claim(client, "CLM-1001")
    assert (record["status"], record["attempts"]) == ("decided", 1)
    assert len(threads(client, "CLM-1001")) == 2
    assert len(decision_calls(client, "CLM-1001")) == 1
    assert claim(client, "CLM-1002")["status"] == "needs_handler"
    assert run_of(client, run_id)["status"] == "finished"


def test_the_summary_is_built_from_the_records(client, script):
    script.decisions["CLM-1001"] = ("approve", 420.0)
    script.decisions["CLM-1003"] = ("approve", 3750.0)
    script.errors["CLM-1004"] = [RuntimeError("the model broke")] * 2
    run_id = dispatch_id(client)
    dispatch(client, run_id, 3, "CLM-1001", "CLM-1002", "CLM-1003", "CLM-1004")
    run = run_of(client, run_id)
    assert run["summary"] == {
        "approved": 2,
        "declined": 1,
        "referred": 0,
        "awaiting_sign_off": [{"claim_id": "CLM-1003", "payout": 3750.0}],
        "needs_handler": ["CLM-1004"],
        "in_progress": [],
    }
    assert claim(client, "CLM-1001")["payment"]["amount"] == 420.0
    assert [c["claim_id"] for c in run["claims"]] == [
        "CLM-1001",
        "CLM-1002",
        "CLM-1003",
        "CLM-1004",
    ]
    assert run["claims"][0]["cost"] == pytest.approx(0.03)
    assert run["claims"][0]["seconds"] > 0
    assert run["cost"] == pytest.approx(0.03 * 3)
    assert run["seconds"] >= 0


def test_a_claim_being_resumed_is_skipped(client, script):
    run_id = dispatch_id(client)
    skip = all_but(client, "CLM-1001", "CLM-1003") | {"CLM-1003"}
    dispatcher.dispatch(run_id, 3, skip, None)
    assert claim(client, "CLM-1003")["status"] == "waiting"
    assert {c for c, _ in script.calls} == {"CLM-1001"}


def test_only_one_claim(client, script):
    run_id = dispatch_id(client, 1)
    assert dispatcher.dispatch(run_id, 1, set(), "CLM-1002") == ["CLM-1002: declined"]
    assert [c["claim_id"] for c in run_of(client, run_id)["claims"]] == ["CLM-1002"]


def test_an_empty_dispatch_finishes(client, script):
    run_id = dispatch_id(client)
    assert dispatcher.dispatch(run_id, 3, all_but(client), None) == []
    assert run_of(client, run_id)["status"] == "finished"


def test_a_failed_dispatch_stops_its_run(client, script, monkeypatch):
    def broken(run_id):
        raise ValueError("the backend broke")

    monkeypatch.setattr(api, "finish_run", broken)
    run_id = dispatch_id(client)
    with pytest.raises(ValueError, match="the backend broke"):
        dispatch(client, run_id, 3, "CLM-1001")
    run = run_of(client, run_id)
    assert (run["status"], run["reason"]) == (
        "stopped",
        "The dispatcher failed: the backend broke",
    )


def test_work_claim_reports_in_one_line(client, script):
    script.decisions["CLM-1001"] = ("approve", 420.0)
    script.decisions["CLM-1003"] = ("approve", 3750.0)
    run_id = dispatch_id(client)
    assert harness.work_claim(run_id, "CLM-1001") == "CLM-1001: approved, $420.00 paid"
    assert harness.work_claim(run_id, "CLM-1003") == (
        "CLM-1003: approved, $3,750.00 waiting for sign-off"
    )
    assert harness.work_claim(run_id, "CLM-1001") == (
        "CLM-1001: not taken. CLM-1001 is not a claim this run can work"
    )
