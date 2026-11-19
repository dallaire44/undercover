from contextlib import contextmanager
from typing import cast

import pytest
from langchain_core.messages import AIMessage

from agent import harness, tools
from agent.tests.conftest import Recorder, StubModel, call, stub

READS = [
    call("get_claim", claim_id="CLM-1001"),
    call("get_policy", policy_id="POL-2001"),
    call("get_claim_history", customer_id="CUS-3001"),
    call("search_documents", query="trip delay meals"),
    call("read_section", document="policy_wording", number="3"),
    call("read_section", document="claims_manual", number="10"),
]


def decide(claim_id, payout):
    return call(
        "record_decision",
        claim_id=claim_id,
        decision="approve",
        payout=payout,
        reason="The wording covers it.",
        policy_section="3. Trip Delay",
    )


def steps(client, claim_id):
    return client.get(f"/api/claims/{claim_id}/steps").json()


def test_a_small_approval_is_paid_straight_away(client):
    harness.run_claim("CLM-1001", "t1", None, stub(*READS, decide("CLM-1001", 420.0)))
    record = client.get("/api/claims/CLM-1001").json()
    assert record["status"] == "decided"
    assert record["payment"]["amount"] == 420.0
    trail = steps(client, "CLM-1001")
    kinds = [s["kind"] for s in trail]
    assert kinds.count("tool_call") == 7
    assert kinds.count("tool_result") + kinds.count("read") == 7
    assert trail[-1]["text"] == "Paid $420.00."
    assert {s["thread_id"] for s in trail} == {"t1"}


def test_the_model_cannot_pay():
    assert "pay_claim" not in [t.name for t in tools.CLAIM_TOOLS]


def test_sections_read_are_steps_of_their_own(client):
    harness.run_claim("CLM-1001", "t1", None, stub(*READS, AIMessage(content="Done.")))
    reads = [s["text"] for s in steps(client, "CLM-1001") if s["kind"] == "read"]
    assert [r.splitlines()[0] for r in reads] == [
        "Policy wording, 3. Trip Delay",
        "Claims manual, 10. Meals without receipts",
    ]


def test_system_prompt_is_the_claim_instructions(client):
    recorder = Recorder(messages=iter([AIMessage(content="Nothing to do.")]))
    recorder.seen.clear()
    harness.run_claim("CLM-1001", "t1", None, recorder)
    first = recorder.seen[0]
    assert first[0].text == client.get("/api/instructions/claim").text
    assert first[1].text == "Decide claim CLM-1001."


class FlakyModel(StubModel):
    """A stub model whose first call fails, as a provider error would."""

    failures: int = 1

    def _generate(self, *args, **kwargs):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("provider unavailable")
        return super()._generate(*args, **kwargs)


def test_a_failed_model_call_is_retried(client, monkeypatch):
    monkeypatch.setattr(harness, "RETRY_DELAY_SECONDS", 0.01)
    replies = [decide("CLM-1001", 0.0), AIMessage(content="Done.")]
    harness.run_claim("CLM-1001", "t1", None, FlakyModel(messages=iter(replies)))
    assert client.get("/api/claims/CLM-1001").json()["decision"] is not None


def test_a_claim_that_loops_is_stopped(client):
    replies = [call("get_claim", claim_id="CLM-1001") for _ in range(40)]
    with pytest.raises(harness.TooManyModelCalls):
        harness.run_claim("CLM-1001", "t1", None, stub(*replies))
    calls = [s for s in steps(client, "CLM-1001") if s["kind"] == "tool_call"]
    assert len(calls) == harness.CLAIM_MODEL_CALLS


def test_blank_messages_are_not_steps():
    message = AIMessage(content="\n\n", tool_calls=[])
    assert harness.steps_of(message) == []


def test_the_payout_tool_works_out_the_payout(client):
    shirts = {
        "description": "Three T-shirts",
        "amount": 74.97,
        "quantity": 3,
        "kind": "item",
        "nights": 0,
        "hours": 0,
    }
    replies = [
        call(
            "calculate_payout",
            policy_id="POL-2007",
            benefit="baggage",
            lines=[shirts],
            paid_by_others=0.0,
        ),
        decide("CLM-1001", 0.0),
        AIMessage(content="Done."),
    ]
    harness.run_claim("CLM-1001", "t1", None, stub(*replies))
    results = [
        s["text"] for s in steps(client, "CLM-1001") if s["kind"] == "tool_result"
    ]
    assert '"step":"Less the deductible"' in results[0]


def test_no_tracing_without_langfuse_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    with harness.tracing("CLM-1001", "t1", "RUN-0002") as config:
        assert config == {}


def test_each_attempt_is_one_langfuse_session_tagged_with_its_run(monkeypatch):
    traced = []

    @contextmanager
    def propagate_attributes(**attributes):
        traced.append(attributes)
        yield

    monkeypatch.setattr(harness, "propagate_attributes", propagate_attributes)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    with harness.tracing("CLM-1001", "t1", "RUN-0002") as config:
        handlers = cast(list, config.get("callbacks"))
        assert [type(h) for h in handlers] == [harness.CallbackHandler]
    with harness.tracing("CLM-1001", "t2", None):
        pass
    assert traced == [
        {"session_id": "CLM-1001 t1", "tags": ["RUN-0002"]},
        {"session_id": "CLM-1001 t2", "tags": None},
    ]


def test_each_claim_run_has_its_own_saver_on_one_pool(monkeypatch):
    assert harness.saver() is harness.saver()
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@localhost:1/none")
    harness.pool.cache_clear()
    try:
        first, second = harness.saver(), harness.saver()
        assert isinstance(first, harness.PostgresSaver)
        assert isinstance(second, harness.PostgresSaver)
        assert first is not second
        assert first.conn is second.conn is harness.pool()
        assert harness.pool().closed
        assert harness.pool().timeout == harness.POOL_WAIT_SECONDS
    finally:
        harness.pool.cache_clear()
