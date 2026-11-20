import runpy

from fastapi.testclient import TestClient

from backend.main import HERE, app


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {c["status"] for c in claims} == {"waiting"}
    assert set(claims[0]) == {
        "claim_id",
        "summary",
        "claim_type",
        "amount_claimed",
        "submitted_on",
        "customer_name",
        "status",
        "attempts",
        "run_id",
        "thread_id",
        "copy_of",
        "decision",
        "payout",
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["customer_name"] == "Maya Patel"
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["sign_off"] is None


def test_unknown_claim(client):
    assert client.get("/api/claims/CLM-9999").status_code == 404


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan_name"] == "UnderCover Premium"
    assert policy["trip"]["destination"] == "Rome, Italy"
    assert policy["travelers"] == ["Maya Patel"]


def test_history_has_no_contact_details(client):
    history = client.get("/api/customers/CUS-3001/history").json()
    assert history["name"] == "Maya Patel"
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    text = str(history)
    for private in ("email", "phone", "address", "date_of_birth"):
        assert private not in text


def test_whole_wording_is_gone(client):
    assert client.get("/api/policy-wording").status_code == 404


def test_instructions(client):
    text = client.get("/api/instructions/claim").text
    assert text == (HERE / "instructions" / "claim.md").read_text(encoding="utf-8")
    assert client.get("/api/instructions/other").status_code == 422


def test_handlers(client):
    assert len(client.get("/api/handlers").json()) == 3


def test_seed_command_twice(client):
    for _ in range(2):
        runpy.run_module("backend.seed", run_name="__main__")
        claims = client.get("/api/claims").json()
        assert [c["status"] for c in claims] == ["waiting"] * 25


def test_first_start_seeds_the_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "new.db"))
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25
