from agent import tools


def test_read_tools(client):
    assert "Maya Patel" in tools.get_claim.invoke({"claim_id": "CLM-1001"})
    assert "Rome" in tools.get_policy.invoke({"policy_id": "POL-2001"})
    history = tools.get_claim_history.invoke({"customer_id": "CUS-3001"})
    assert "CLM-0412" in history


def test_lookup_tools(client):
    assert "- 9. Repeat claims" in tools.list_sections.invoke({})
    found = tools.search_documents.invoke({"query": "wild animals"})
    assert found.startswith("Claims manual, 7. Interpretation notes")
    section = tools.read_section.invoke({"document": "claims_manual", "number": "10"})
    assert section.startswith("Claims manual, 10. Meals without receipts")


def test_refusal_goes_back_to_the_model(client):
    reply = tools.get_claim.invoke({"claim_id": "CLM-9999"})
    assert reply == "Refused (404): CLM-9999 not found"


def test_blocked_payment_message(client):
    tools.record_decision.invoke(
        {
            "claim_id": "CLM-1003",
            "decision": "approve",
            "payout": 3750.0,
            "reason": "Covered.",
            "policy_section": "5. Baggage",
        }
    )
    reply = tools.pay_claim.invoke({"claim_id": "CLM-1003", "amount": 3750.0})
    assert "needs a handler's sign-off" in reply
