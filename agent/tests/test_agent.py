from langchain_core.messages import AIMessage, HumanMessage

from agent import main
from agent.tests.conftest import stub, tool_call


def steps(api, claim_id):
    return api.get(f"/api/claims/{claim_id}/steps").json()


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"


def test_system_prompt_is_the_backends_instructions(api):
    llm = stub(AIMessage(content="Nothing to do."))
    main.run("CLM-1001", "t1", llm)
    expected = api.get("/api/instructions").json()["text"]
    assert llm.seen[0][0].content == expected


def test_approve_and_pay_decides_the_claim(api):
    llm = stub(
        AIMessage(
            content="I'll read the claim.",
            tool_calls=[
                tool_call("get_claim", claim_id="CLM-1001"),
                tool_call("get_policy", policy_id="POL-2001"),
                tool_call("get_claim_history", customer_id="CUS-3001"),
                tool_call("get_policy_wording"),
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                tool_call(
                    "record_decision",
                    claim_id="CLM-1001",
                    decision="approve",
                    payout=420.0,
                    reason="Covered delay costs.",
                    policy_section="Section 3, Trip Delay",
                )
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[tool_call("pay_claim", claim_id="CLM-1001", amount=420.0)],
        ),
        AIMessage(content="Approved and paid $420.00."),
    )
    reply = main.run("CLM-1001", "t1", llm)
    assert reply == "Approved and paid $420.00."
    claim = api.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0
    kinds = [s["kind"] for s in steps(api, "CLM-1001")]
    assert kinds.count("message") == 2
    assert kinds.count("tool_call") == 6
    assert kinds.count("tool_result") == 6
    assert {s["thread_id"] for s in steps(api, "CLM-1001")} == {"t1"}


def test_blocked_payment_is_shown_to_the_model(api):
    decide = tool_call(
        "record_decision",
        claim_id="CLM-1003",
        decision="approve",
        payout=3750.0,
        reason="Covered.",
        policy_section="Section 5",
    )
    llm = stub(
        AIMessage(content="", tool_calls=[decide]),
        AIMessage(
            content="",
            tool_calls=[tool_call("pay_claim", claim_id="CLM-1003", amount=3750.0)],
        ),
        AIMessage(content="The payment needs a handler's sign-off."),
    )
    main.run("CLM-1003", "t1", llm)
    claim = api.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "awaiting_sign_off"
    assert claim["payment"] is None
    results = [s["text"] for s in steps(api, "CLM-1003") if s["kind"] == "tool_result"]
    assert (
        "Refused (409): A payout over $1,000.00 needs a handler's sign-off"
        in results[-1]
    )


def test_other_messages_make_no_steps():
    assert main.steps_of(HumanMessage(content="hi")) == []
