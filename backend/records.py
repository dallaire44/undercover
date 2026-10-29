"""Read the records: claims, policies, customers and handlers."""

import json
import sqlite3

from fastapi import HTTPException

from backend import db
from backend.models import (
    ClaimDetail,
    ClaimSummary,
    CustomerHistory,
    DecisionRecord,
    Handler,
    Payment,
    Policy,
    SignOff,
)

LIST_CLAIMS = """
SELECT c.status, c.doc, d.decision, d.payout
FROM claims c LEFT JOIN decisions d ON d.claim_id = c.claim_id
ORDER BY c.claim_id
"""


def document(conn: sqlite3.Connection, table: str, key: str, value: str) -> dict:
    """Return one stored record, or raise 404."""
    query = f"SELECT doc FROM {table} WHERE {key} = ?"  # noqa: S608
    row = conn.execute(query, (value,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{value} not found")
    return json.loads(row["doc"])


def one(conn: sqlite3.Connection, table: str, claim_id: str) -> sqlite3.Row | None:
    """Return a claim's row in one of the tables keyed by claim id."""
    query = f"SELECT * FROM {table} WHERE claim_id = ?"  # noqa: S608
    return conn.execute(query, (claim_id,)).fetchone()


def status(conn: sqlite3.Connection, claim_id: str) -> str:
    """Return a claim's state, or raise 404."""
    row = conn.execute(
        "SELECT status FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"{claim_id} not found")
    return row["status"]


def list_claims(conn: sqlite3.Connection) -> list[ClaimSummary]:
    """Return every claim in the queue, with its decision and payout if any."""
    customers = conn.execute("SELECT doc FROM customers").fetchall()
    names = {
        c["customer_id"]: c["name"] for c in (json.loads(r["doc"]) for r in customers)
    }
    summaries = []
    for row in conn.execute(LIST_CLAIMS).fetchall():
        claim = json.loads(row["doc"])
        summaries.append(
            ClaimSummary(
                **{**claim, "status": row["status"]},
                customer_name=names[claim["customer_id"]],
                decision=row["decision"],
                payout=row["payout"],
            )
        )
    return summaries


def signed_off(conn: sqlite3.Connection, row: sqlite3.Row) -> SignOff:
    """Return a sign-off with the handler's name."""
    handler = document(conn, "handlers", "handler_id", row["handler_id"])
    return SignOff(**row, handler_name=handler["name"])


def get_claim(conn: sqlite3.Connection, claim_id: str) -> ClaimDetail:
    """Return one claim in full, with its decision, payment and sign-off."""
    claim = document(conn, "claims", "claim_id", claim_id)
    customer = document(conn, "customers", "customer_id", claim["customer_id"])
    decision, payment, sign_off = (
        one(conn, t, claim_id) for t in ("decisions", "payments", "sign_offs")
    )
    return ClaimDetail(
        **{**claim, "status": status(conn, claim_id)},
        customer_name=customer["name"],
        decision=DecisionRecord(**decision) if decision else None,
        payment=Payment(**payment) if payment else None,
        sign_off=signed_off(conn, sign_off) if sign_off else None,
    )


def get_policy(conn: sqlite3.Connection, policy_id: str) -> Policy:
    """Return a policy with the name of its plan."""
    policy = document(conn, "policies", "policy_id", policy_id)
    plans = {p["plan"]: p["name"] for p in db.load("plans")["plans"]}
    return Policy(**policy, plan_name=plans[policy["plan"]])


def get_history(conn: sqlite3.Connection, customer_id: str) -> CustomerHistory:
    """Return a customer's name and earlier claims, with no contact details."""
    return CustomerHistory(**document(conn, "customers", "customer_id", customer_id))


def list_handlers(conn: sqlite3.Connection) -> list[Handler]:
    """Return the claims handlers."""
    rows = conn.execute("SELECT doc FROM handlers ORDER BY handler_id").fetchall()
    return [Handler(**json.loads(row["doc"])) for row in rows]
