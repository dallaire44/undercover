import pytest
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain_core.messages import AIMessage

from agent import claim, model
from agent.tests.conftest import StubModel, call, stub

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


def test_run_pays_a_small_approval(client):
    replies = [
        *READS,
        decide("CLM-1001", 420.0),
        call("pay_claim", claim_id="CLM-1001", amount=420.0),
        AIMessage(content="Approved, $420.00 paid."),
    ]
    assert claim.run("CLM-1001", "t1", stub(*replies)) == "Approved, $420.00 paid."
    record = client.get("/api/claims/CLM-1001").json()
    assert record["status"] == "decided"
    assert record["payment"]["amount"] == 420.0
    trail = steps(client, "CLM-1001")
    kinds = [s["kind"] for s in trail]
    assert kinds.count("tool_call") == 8
    assert kinds.count("tool_result") == 6
    assert trail[-1]["kind"] == "message"
    assert {s["thread_id"] for s in trail} == {"t1"}


def test_sections_read_are_steps_of_their_own(client):
    claim.run("CLM-1001", "t1", stub(*READS, AIMessage(content="Done.")))
    reads = [s["text"] for s in steps(client, "CLM-1001") if s["kind"] == "read"]
    assert [r.splitlines()[0] for r in reads] == [
        "Policy wording, 3. Trip Delay",
        "Claims manual, 10. Meals without receipts",
    ]


def test_run_cannot_pay_over_the_limit(client):
    replies = [
        decide("CLM-1003", 3750.0),
        call("pay_claim", claim_id="CLM-1003", amount=3750.0),
        AIMessage(content="Waiting for sign-off."),
    ]
    claim.run("CLM-1003", "t1", stub(*replies))
    record = client.get("/api/claims/CLM-1003").json()
    assert record["status"] == "awaiting_sign_off"
    assert record["payment"] is None
    results = [
        s["text"] for s in steps(client, "CLM-1003") if s["kind"] == "tool_result"
    ]
    assert "needs a handler's sign-off" in results[-1]


def test_system_prompt_is_the_claim_instructions(client, monkeypatch):
    seen = {}
    real = claim.create_agent

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(claim, "create_agent", spy)
    claim.run("CLM-1001", "t1", stub(AIMessage(content="Nothing to do.")))
    assert seen["system_prompt"] == client.get("/api/instructions/claim").text


class FlakyModel(StubModel):
    """A stub model whose first call fails, as a provider error would."""

    failures: int = 1

    def _generate(self, *args, **kwargs):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("provider unavailable")
        return super()._generate(*args, **kwargs)


def test_a_failed_model_call_is_retried(client, monkeypatch):
    monkeypatch.setattr(model, "RETRY_DELAY_SECONDS", 0.01)
    replies = [decide("CLM-1001", 0.0), AIMessage(content="Done.")]
    claim.run("CLM-1001", "t1", FlakyModel(messages=iter(replies)))
    assert client.get("/api/claims/CLM-1001").json()["decision"] is not None


def test_a_claim_that_loops_is_stopped(client):
    replies = [call("get_claim", claim_id="CLM-1001") for _ in range(40)]
    with pytest.raises(ModelCallLimitExceededError):
        claim.run("CLM-1001", "t1", stub(*replies))
    calls = [s for s in steps(client, "CLM-1001") if s["kind"] == "tool_call"]
    assert len(calls) == model.CLAIM_MODEL_CALLS


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = model.model()
    assert default.model_name == "deepseek/deepseek-v4.1-flash"
    assert default.reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert model.model().model_name == "openrouter/free"


def test_blank_messages_are_not_steps():
    message = AIMessage(content="\n\n", tool_calls=[])
    assert claim.steps_of(message) == []
