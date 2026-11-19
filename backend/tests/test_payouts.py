from backend import db


def line(description, amount, kind="item", quantity=1):
    return {
        "description": description,
        "amount": amount,
        "quantity": quantity,
        "kind": kind,
        "nights": 0,
        "hours": 0,
    }


def payout(client, policy_id, benefit, lines, paid_by_others=0.0):
    body = {"benefit": benefit, "lines": lines, "paid_by_others": paid_by_others}
    return client.post(f"/api/policies/{policy_id}/payout", json=body)


def test_items_are_limited_and_others_and_the_deductible_taken_off(client):
    lines = [
        line("Hard-shell suitcase", 239.99),
        line("Three T-shirts", 74.97, quantity=3),
    ]
    result = payout(client, "POL-2007", "baggage", lines, 100.0).json()
    assert result["calculation"] == [
        {"step": "Hard-shell suitcase, limited to $150.00", "amount": 150.0},
        {"step": "Three T-shirts", "amount": 74.97},
        {"step": "Less what others have paid or refunded", "amount": -100.0},
        {"step": "Less the deductible", "amount": -100.0},
    ]
    assert result["payout"] == 24.97
    assert result["needs_sign_off"] is False


def test_a_payout_over_the_limit_needs_sign_off(client):
    lines = [line("Hospital bill", 3800.0, kind="expense")]
    result = payout(client, "POL-2006", "emergency_medical", lines).json()
    assert result["payout"] == 3800.0
    assert result["needs_sign_off"] is True


def test_the_limit_comes_from_the_company_settings(client, monkeypatch):
    load = db.load
    company = {**load("company"), "payout_approval_limit": 5000.0}
    monkeypatch.setattr(
        db, "load", lambda name: company if name == "company" else load(name)
    )
    lines = [line("Hospital bill", 3800.0, kind="expense")]
    result = payout(client, "POL-2006", "emergency_medical", lines).json()
    assert result["needs_sign_off"] is False


def test_cash_is_limited_to_100_in_all(client):
    lines = [line("Wallet cash", 80.0, "cash"), line("Pocket cash", 70.0, "cash")]
    result = payout(client, "POL-2006", "baggage", lines).json()
    assert {"step": "Cash, up to $100 in all", "amount": 100.0} in result["calculation"]


def test_an_unknown_policy_is_not_found(client):
    assert payout(client, "POL-9999", "baggage", []).status_code == 404


def test_every_input_is_required(client):
    body = {"benefit": "baggage", "lines": [{"description": "Bag", "amount": 10}]}
    response = client.post("/api/policies/POL-2006/payout", json=body)
    assert response.status_code == 422
