import pytest

from backend.tests.conftest import decide, pay, status

LIMIT_MESSAGE = "A payout over $1,000.00 needs a handler's sign-off"


def sign_off(client, claim_id, handler_id="HND-01"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def test_small_approval_is_paid(client):
    assert decide(client, "CLM-1001", payout=420.0).status_code == 200
    assert status(client, "CLM-1001") == "in_progress"
    assert pay(client, "CLM-1001", 420.0).status_code == 200
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0


def test_large_approval_cannot_be_paid(client):
    decide(client, "CLM-1003", payout=3750.0)
    assert status(client, "CLM-1003") == "awaiting_sign_off"
    response = pay(client, "CLM-1003", 3750.0)
    assert response.status_code == 409
    assert LIMIT_MESSAGE in response.json()["detail"]
    assert client.get("/api/claims/CLM-1003").json()["payment"] is None


def test_sign_off_does_not_pay(client):
    decide(client, "CLM-1003", payout=3750.0)
    response = sign_off(client, "CLM-1003", "HND-03")
    assert response.json()["handler_name"] == "Priya Raman"
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "in_progress"
    assert claim["payment"] is None
    assert sign_off(client, "CLM-1003").status_code == 409


def test_the_payment_records_the_sign_off(client):
    decide(client, "CLM-1003", payout=3750.0)
    signed = sign_off(client, "CLM-1003", "HND-03").json()
    claim = pay(client, "CLM-1003", 3750.0).json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 3750.0
    assert claim["payment"]["signed_off_by"] == "Priya Raman"
    assert claim["payment"]["signed_off_at"] == signed["signed_at"]


def test_a_small_payment_has_no_sign_off(client):
    decide(client, "CLM-1001", payout=420.0)
    payment = pay(client, "CLM-1001", 420.0).json()["payment"]
    assert (payment["signed_off_by"], payment["signed_off_at"]) == (None, None)


def test_a_repeated_decision_counts_as_done(client):
    first = decide(client, "CLM-1001", payout=420.0)
    again = decide(client, "CLM-1001", payout=420.0)
    assert first.status_code == again.status_code == 200
    assert again.json()["claim_id"] == "CLM-1001"
    assert (
        again.json()["decision"]["decided_at"] == first.json()["decision"]["decided_at"]
    )
    declined = decide(client, "CLM-1001", decision="decline", payout=0.0)
    assert declined.status_code == 409
    assert "already has a decision" in declined.json()["detail"]
    assert decide(client, "CLM-1001", payout=400.0).status_code == 409


def test_a_repeated_decline_counts_as_done(client):
    decide(client, "CLM-1001", decision="decline", payout=0.0)
    assert decide(client, "CLM-1001", decision="decline", payout=0.0).status_code == 200


def test_a_repeated_payment_counts_as_done(client):
    decide(client, "CLM-1001", payout=420.0)
    first = pay(client, "CLM-1001", 420.0).json()
    again = pay(client, "CLM-1001", 420.0)
    assert again.status_code == 200
    assert again.json()["status"] == "decided"
    assert again.json()["payment"]["paid_at"] == first["payment"]["paid_at"]
    assert pay(client, "CLM-1001", 400.0).status_code == 409


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_no_payment_after_decline_or_refer(client, decision):
    decide(client, "CLM-1001", decision=decision, payout=500.0)
    assert pay(client, "CLM-1001", 500.0).status_code == 409


def test_cannot_pay_without_a_decision(client):
    assert pay(client, "CLM-1001", 100.0).status_code == 409


def test_cannot_pay_a_different_amount(client):
    decide(client, "CLM-1001", payout=420.0)
    assert pay(client, "CLM-1001", 400.0).status_code == 409
    assert status(client, "CLM-1001") == "in_progress"


def test_sign_off_needs_a_claim_waiting_for_it(client):
    assert sign_off(client, "CLM-1001").status_code == 409
    decide(client, "CLM-1001", payout=420.0)
    assert sign_off(client, "CLM-1001").status_code == 409


def test_sign_off_by_an_unknown_handler(client):
    decide(client, "CLM-1003", payout=3750.0)
    assert sign_off(client, "CLM-1003", "HND-99").status_code == 404


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_and_refer_finish_the_claim(client, decision):
    decide(client, "CLM-1001", decision=decision, payout=500.0)
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["decision"]["payout"] == 0
    assert decide(client, "CLM-1001").status_code == 409


def test_decision_must_be_valid(client):
    assert decide(client, "CLM-1001", decision="maybe").status_code == 422
    assert decide(client, "CLM-1001", payout=-1.0).status_code == 422


def test_unknown_claim(client):
    assert decide(client, "CLM-9999").status_code == 404
    assert pay(client, "CLM-9999", 1.0).status_code == 404
    assert sign_off(client, "CLM-9999").status_code == 404


def test_list_claims_shows_decision_and_payout(client):
    decide(client, "CLM-1001", payout=420.0)
    claims = {c["claim_id"]: c for c in client.get("/api/claims").json()}
    assert claims["CLM-1001"]["decision"] == "approve"
    assert claims["CLM-1001"]["payout"] == 420.0
    assert claims["CLM-1002"]["decision"] is None
    assert claims["CLM-1002"]["payout"] is None
