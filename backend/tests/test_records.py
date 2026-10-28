from concurrent.futures import ThreadPoolExecutor

from backend import db
from backend.seed import reset


def test_queue_has_25_waiting_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {c["status"] for c in claims} == {"waiting"}
    first = claims[0]
    for key in (
        "claim_id",
        "summary",
        "claim_type",
        "amount_claimed",
        "submitted_on",
        "customer_name",
    ):
        assert first[key]


def test_get_claim_in_full(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["customer_name"] == "Maya Patel"
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["sign_off"] is None


def test_unknown_claim_is_404(client):
    assert client.get("/api/claims/CLM-9999").status_code == 404


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["destination"] == "Rome, Italy"
    assert policy["travelers"] == ["Maya Patel"]
    assert client.get("/api/policies/POL-0000").status_code == 404


def test_claim_history_leaves_out_contact_details(client):
    history = client.get("/api/customers/CUS-3001/history").json()
    assert history["name"] == "Maya Patel"
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    for private in ("email", "phone", "address", "date_of_birth"):
        assert private not in history
    assert client.get("/api/customers/CUS-0000/history").status_code == 404


def test_policy_wording(client):
    text = client.get("/api/policy-wording").json()["text"]
    assert text.startswith("# UnderCover Travel Insurance: Policy Wording")


def test_instructions(client):
    text = client.get("/api/instructions").json()["text"]
    assert text.startswith("# Instructions for the UnderCover Agent")
    assert "section 10" in text


def test_handlers(client):
    assert len(client.get("/api/handlers").json()) == 3


def test_reset_twice_leaves_25_waiting_claims(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "reset.db"))
    reset()
    reset()
    conn = db.connect()
    waiting = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE status = 'waiting'"
    ).fetchone()[0]
    assert waiting == 25


def test_a_connection_can_move_between_threads(tmp_path, monkeypatch):
    """FastAPI opens a request's connection in one thread and uses it in another."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "threads.db"))
    conn = db.connect()
    with ThreadPoolExecutor() as pool:
        count = pool.submit(
            lambda: conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        )
        assert count.result() == 25
