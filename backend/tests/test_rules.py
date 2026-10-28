def decide(client, claim_id, decision="approve", payout=0.0, **extra):
    body = {
        "decision": decision,
        "payout": payout,
        "reason": "Because the wording says so.",
        "policy_section": "Section 3, Trip Delay",
    }
    return client.post(f"/api/claims/{claim_id}/decision", json={**body, **extra})


def pay(client, claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, claim_id, handler_id="HND-01"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def status(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def test_approve_under_the_limit_then_pay(client):
    assert decide(client, "CLM-1001", payout=420.00).status_code == 200
    assert status(client, "CLM-1001") == "in_progress"
    paid = pay(client, "CLM-1001", 420.00)
    assert paid.status_code == 200
    assert paid.json()["status"] == "decided"
    assert paid.json()["payment"]["amount"] == 420.00


def test_payout_over_the_limit_waits_for_sign_off(client):
    decide(client, "CLM-1003", payout=3750.00)
    assert status(client, "CLM-1003") == "awaiting_sign_off"
    refused = pay(client, "CLM-1003", 3750.00)
    assert refused.status_code == 409
    assert "A payout over $1,000.00 needs a handler's sign-off" in refused.text
    assert client.get("/api/claims/CLM-1003").json()["payment"] is None


def test_the_limit_itself_does_not_need_sign_off(client):
    decide(client, "CLM-1001", payout=1000.00)
    assert status(client, "CLM-1001") == "in_progress"
    assert pay(client, "CLM-1001", 1000.00).status_code == 200


def test_sign_off_pays_the_claim(client):
    decide(client, "CLM-1003", payout=3750.00)
    done = sign_off(client, "CLM-1003").json()
    assert done["status"] == "decided"
    assert done["sign_off"]["handler_name"] == "Dana Whitfield"
    assert done["payment"]["amount"] == 3750.00
    assert pay(client, "CLM-1003", 3750.00).status_code == 409


def test_pay_claim_refuses_what_it_should(client):
    assert pay(client, "CLM-1001", 10).status_code == 409
    decide(client, "CLM-1002", "decline")
    assert pay(client, "CLM-1002", 0).status_code == 409
    decide(client, "CLM-1004", "refer")
    assert pay(client, "CLM-1004", 0).status_code == 409
    decide(client, "CLM-1001", payout=420.00)
    assert pay(client, "CLM-1001", 400.00).status_code == 409
    assert pay(client, "CLM-1001", 420.00).status_code == 200
    assert pay(client, "CLM-1001", 420.00).status_code == 409
    assert pay(client, "CLM-9999", 1).status_code == 404


def test_sign_off_refuses_what_it_should(client):
    decide(client, "CLM-1001", payout=420.00)
    assert sign_off(client, "CLM-1001").status_code == 409
    decide(client, "CLM-1003", payout=3750.00)
    assert sign_off(client, "CLM-1003", "HND-99").status_code == 404
    assert sign_off(client, "CLM-9999").status_code == 404


def test_decline_and_refer_finish_the_claim_with_no_payout(client):
    for claim_id, decision in (("CLM-1002", "decline"), ("CLM-1004", "refer")):
        done = decide(client, claim_id, decision, payout=99.0).json()
        assert done["status"] == "decided"
        assert done["decision"]["payout"] == 0
        assert decide(client, claim_id, "approve", 5.0).status_code == 409
    assert decide(client, "CLM-9999").status_code == 404


def test_record_decision_validates_its_input(client):
    assert decide(client, "CLM-1001", "maybe").status_code == 422
    assert decide(client, "CLM-1001", payout=-1.0).status_code == 422
    assert status(client, "CLM-1001") == "waiting"


def test_queue_shows_decision_and_payout(client):
    undecided = client.get("/api/claims").json()[0]
    assert undecided["decision"] is None
    assert undecided["payout"] is None
    decide(client, "CLM-1001", payout=420.00)
    first = client.get("/api/claims").json()[0]
    assert (first["decision"], first["payout"]) == ("approve", 420.00)
    decide(client, "CLM-1002", "decline")
    second = client.get("/api/claims").json()[1]
    assert (second["decision"], second["payout"]) == ("decline", 0)


def test_steps_are_stored_oldest_first(client):
    for kind, text in (("message", "Reading"), ("tool_call", "get_claim")):
        step = {"thread_id": "t1", "kind": kind, "text": text}
        assert client.post("/api/claims/CLM-1001/steps", json=step).status_code == 200
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [s["text"] for s in steps] == ["Reading", "get_claim"]
    assert steps[0]["thread_id"] == "t1"
    assert steps[0]["kind"] == "message"
    assert client.get("/api/claims/CLM-1002/steps").json() == []


def test_steps_check_the_claim_and_the_kind(client):
    step = {"thread_id": "t1", "kind": "message", "text": "x"}
    assert client.post("/api/claims/CLM-9999/steps", json=step).status_code == 404
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404
    bad = {**step, "kind": "shout"}
    assert client.post("/api/claims/CLM-1001/steps", json=bad).status_code == 422
