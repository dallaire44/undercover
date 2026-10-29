from langchain_core.messages import AIMessage

from agent import main
from agent.tests.conftest import call, stub

READS = [
    call("get_claim", claim_id="CLM-1001"),
    call("get_policy", policy_id="POL-2001"),
    call("get_claim_history", customer_id="CUS-3001"),
    call("get_policy_wording"),
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
        AIMessage(content="Approved and paid."),
    ]
    assert main.run("CLM-1001", "t1", stub(*replies)) == "Approved and paid."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0
    trail = steps(client, "CLM-1001")
    assert [s["kind"] for s in trail].count("tool_call") == 6
    assert [s["kind"] for s in trail].count("tool_result") == 6
    assert trail[-1]["kind"] == "message"
    assert {s["thread_id"] for s in trail} == {"t1"}


def test_run_cannot_pay_over_the_limit(client):
    replies = [
        decide("CLM-1003", 3750.0),
        call("pay_claim", claim_id="CLM-1003", amount=3750.0),
        AIMessage(content="Waiting for sign-off."),
    ]
    main.run("CLM-1003", "t1", stub(*replies))
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "awaiting_sign_off"
    assert claim["payment"] is None
    results = [
        s["text"] for s in steps(client, "CLM-1003") if s["kind"] == "tool_result"
    ]
    assert "needs a handler's sign-off" in results[-1]


def test_system_prompt_is_the_instructions(client, monkeypatch):
    seen = {}
    real = main.create_agent

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(main, "create_agent", spy)
    main.run("CLM-1001", "t1", stub(AIMessage(content="Nothing to do.")))
    assert seen["system_prompt"] == client.get("/api/instructions").text


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
