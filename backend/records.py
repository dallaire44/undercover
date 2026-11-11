"""Read the records: claims, policies, customers and handlers."""

import json
import sqlite3
from typing import Any

from backend import db
from backend.errors import NotFound
from backend.models import (
    ClaimDetail,
    ClaimSummary,
    CustomerHistory,
    DecisionRecord,
    Handler,
    Payment,
    Policy,
    SignOff,
    State,
)

CLAIMS = """
SELECT c.status, c.attempts, c.doc, d.decision, d.payout,
    json_extract(cu.doc, '$.name') AS customer_name
FROM claims c
JOIN customers cu ON cu.customer_id = json_extract(c.doc, '$.customer_id')
LEFT JOIN decisions d ON d.claim_id = c.claim_id
WHERE :claim_id IS NULL OR c.claim_id = :claim_id
ORDER BY c.claim_id
"""


def document(conn: sqlite3.Connection, table: str, value: str) -> dict[str, Any]:
    """Return one stored claim, policy, customer or handler, or raise NotFound."""
    query = f"SELECT doc FROM {table} WHERE {db.DOCUMENTS[table]} = ?"  # noqa: S608
    row = conn.execute(query, (value,)).fetchone()
    if row is None:
        raise NotFound(f"{value} not found")
    return json.loads(row["doc"])


def one(conn: sqlite3.Connection, table: str, claim_id: str) -> sqlite3.Row | None:
    """Return a claim's row in one of the tables keyed by claim id."""
    query = f"SELECT * FROM {table} WHERE claim_id = ?"  # noqa: S608
    return conn.execute(query, (claim_id,)).fetchone()


def claim_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    """Return a claim's state, attempts and record, or raise NotFound."""
    row = conn.execute(
        "SELECT status, attempts, doc FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise NotFound(f"{claim_id} not found")
    return row


def status(conn: sqlite3.Connection, claim_id: str) -> State:
    """Return a claim's state, or raise NotFound."""
    return claim_row(conn, claim_id)["status"]


def summaries(conn: sqlite3.Connection, claim_id: str | None) -> list[ClaimSummary]:
    """Return the claims as they show in the queue: all of them, or just one."""
    return [
        ClaimSummary(
            **{**json.loads(row["doc"]), "status": row["status"]},
            attempts=row["attempts"],
            customer_name=row["customer_name"],
            decision=row["decision"],
            payout=row["payout"],
        )
        for row in conn.execute(CLAIMS, {"claim_id": claim_id})
    ]


def list_claims(conn: sqlite3.Connection) -> list[ClaimSummary]:
    """Return every claim in the queue, with its decision and payout if any."""
    return summaries(conn, None)


def summary(conn: sqlite3.Connection, claim_id: str) -> ClaimSummary:
    """Return one claim, known to exist, as it shows in the queue."""
    (found,) = summaries(conn, claim_id)
    return found


def signed_off(conn: sqlite3.Connection, row: sqlite3.Row) -> SignOff:
    """Return a sign-off with the handler's name."""
    handler = document(conn, "handlers", row["handler_id"])
    return SignOff(**row, handler_name=handler["name"])


def get_claim(conn: sqlite3.Connection, claim_id: str) -> ClaimDetail:
    """Return one claim in full, with its decision, payment and sign-off."""
    row = claim_row(conn, claim_id)
    claim = json.loads(row["doc"])
    customer = document(conn, "customers", claim["customer_id"])
    decision, payment, sign_off = (
        one(conn, t, claim_id) for t in ("decisions", "payments", "sign_offs")
    )
    return ClaimDetail(
        **{**claim, "status": row["status"], "attempts": row["attempts"]},
        customer_name=customer["name"],
        decision=DecisionRecord(**decision) if decision else None,
        payment=Payment(**payment) if payment else None,
        sign_off=signed_off(conn, sign_off) if sign_off else None,
    )


def get_policy(conn: sqlite3.Connection, policy_id: str) -> Policy:
    """Return a policy with the name of its plan."""
    policy = document(conn, "policies", policy_id)
    plans = {p["plan"]: p["name"] for p in db.load("plans")["plans"]}
    return Policy(**policy, plan_name=plans[policy["plan"]])


def get_history(conn: sqlite3.Connection, customer_id: str) -> CustomerHistory:
    """Return a customer's name and earlier claims, with no contact details."""
    return CustomerHistory(**document(conn, "customers", customer_id))


def list_handlers(conn: sqlite3.Connection) -> list[Handler]:
    """Return the claims handlers."""
    rows = conn.execute("SELECT doc FROM handlers ORDER BY handler_id").fetchall()
    return [Handler(**json.loads(row["doc"])) for row in rows]
