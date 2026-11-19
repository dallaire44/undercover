import pytest
from langchain_core.messages import AIMessage, ToolMessage

from agent import harness
from agent.tests.conftest import Recorder, StopsOnce, call, dispatch_id, stub

READS = [
    call("get_claim", claim_id="CLM-1001"),
    call("get_policy", policy_id="POL-2001"),
    call("get_claim_history", customer_id="CUS-3001"),
]


def approve(claim_id, payout):
    return call(
        "record_decision",
        claim_id=claim_id,
        decision="approve",
        payout=payout,
        reason="The wording covers it.",
        policy_section="3. Trip Delay",
    )


class Broken(Recorder):
    """A stub model whose every call fails with an error that is not retried."""

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(list(messages))
        raise RuntimeError("the model broke")


@pytest.fixture
def run_id(client):
    """A running dispatch, which no agent works until a test does."""
    return dispatch_id(client)


def claim(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()


def thread(thread_id):
    graph = harness.claim_graph()
    return graph.get_state({"configurable": {"thread_id": thread_id}})


def steps(client, claim_id):
    return [s["text"] for s in client.get(f"/api/claims/{claim_id}/steps").json()]


def test_the_graph_waits_before_a_payout_over_the_limit(client):
    harness.run_claim("CLM-1003", "t1", None, stub(approve("CLM-1003", 3750.0)))
    record = claim(client, "CLM-1003")
    assert record["status"] == "awaiting_sign_off"
    assert record["payment"] is None
    saved = thread("t1")
    assert saved.next == ("sign_off",)
    assert saved.interrupts[0].value == {"claim_id": "CLM-1003", "payout": 3750.0}
    assert steps(client, "CLM-1003")[-1] == "Waiting for a handler's sign-off."


def test_a_sign_off_resumes_the_claim_and_pays_it_once(client):
    harness.run_claim("CLM-1003", "t1", None, stub(approve("CLM-1003", 3750.0)))
    client.post("/api/claims/CLM-1003/sign-off", json={"handler_id": "HND-03"})
    assert claim(client, "CLM-1003")["status"] == "in_progress"
    idle = Recorder(messages=iter([]))
    harness.run_claim("CLM-1003", "t1", None, idle)
    harness.run_claim("CLM-1003", "t1", None, idle)
    assert idle.seen == []
    record = claim(client, "CLM-1003")
    assert record["status"] == "decided"
    assert record["payment"]["amount"] == 3750.0
    assert record["payment"]["signed_off_by"] == "Priya Raman"
    assert steps(client, "CLM-1003")[-2:] == [
        "Signed off by Priya Raman.",
        "Paid $3,750.00.",
    ]


def test_no_resume_before_the_sign_off(client):
    harness.run_claim("CLM-1003", "t1", None, stub(approve("CLM-1003", 3750.0)))
    harness.run_claim("CLM-1003", "t1", None, Recorder(messages=iter([])))
    assert thread("t1").next == ("sign_off",)
    assert claim(client, "CLM-1003")["payment"] is None


def test_a_claim_stopped_partway_carries_on_from_its_last_step(
    client, run_id, monkeypatch
):
    model_ = StopsOnce(messages=iter([*READS, approve("CLM-1001", 420.0)]))
    monkeypatch.setattr(harness, "model", lambda: model_)
    with pytest.raises(KeyboardInterrupt):
        harness.work_claim(run_id, "CLM-1001")
    stopped = claim(client, "CLM-1001")
    assert stopped["status"] == "in_progress"

    harness.work_claim(run_id, "CLM-1001")
    record = claim(client, "CLM-1001")
    assert record["status"] == "decided"
    assert record["thread_id"] == stopped["thread_id"]
    assert record["attempts"] == 0
    assert record["payment"]["amount"] == 420.0
    carried_on = model_.seen[-1]
    assert [m.name for m in carried_on if isinstance(m, ToolMessage)] == [
        "get_claim",
        "get_policy",
        "get_claim_history",
    ]
    assert steps(client, "CLM-1001").count("Agent started") == 1


def test_a_claim_that_fails_with_an_error_starts_afresh(client, run_id, monkeypatch):
    second = Recorder(messages=iter([AIMessage(content="Not sure.")]))
    second.seen.clear()
    models = iter([Broken(messages=iter([])), second])
    monkeypatch.setattr(harness, "model", lambda: next(models))
    line = harness.work_claim(run_id, "CLM-1001")
    assert line.startswith("CLM-1001: failed twice, left for a handler.")
    returned = claim(client, "CLM-1001")
    assert (returned["status"], returned["attempts"]) == ("needs_handler", 2)
    first = second.seen[0]
    assert [m.text for m in first[1:]] == ["Decide claim CLM-1001."]
    trail = client.get("/api/claims/CLM-1001/steps").json()
    assert len({s["thread_id"] for s in trail}) == 2


def test_a_repeated_decision_counts_as_done(client):
    body = {
        "decision": "approve",
        "payout": 420.0,
        "reason": "The wording covers it.",
        "policy_section": "3. Trip Delay",
    }
    before = client.post("/api/claims/CLM-1001/decision", json=body).json()
    harness.run_claim("CLM-1001", "t1", None, stub(approve("CLM-1001", 420.0)))
    record = claim(client, "CLM-1001")
    assert record["decision"]["decided_at"] == before["decision"]["decided_at"]
    assert record["status"] == "decided"
    assert record["payment"]["amount"] == 420.0


def test_a_refused_call_goes_back_to_the_model_as_text(client):
    model_ = Recorder(
        messages=iter([approve("CLM-9999", 420.0), AIMessage(content="I'll stop.")])
    )
    harness.run_claim("CLM-1001", "t1", None, model_)
    refusal = model_.seen[1][-1]
    assert isinstance(refusal, ToolMessage)
    assert refusal.text == "Refused (404): CLM-9999 not found"
    assert claim(client, "CLM-1001")["decision"] is None
