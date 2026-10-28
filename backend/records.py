"""Read operations over the seeded records."""

import json
import sqlite3

from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Handler,
    Payment,
    Policy,
    SignOff,
)


def _load(db: sqlite3.Connection, table: str, key: str, value: str) -> dict | None:
    row = db.execute(
        f"SELECT data FROM {table} WHERE {key} = ?",  # noqa: S608
        (value,),
    ).fetchone()
    return json.loads(row["data"]) if row else None


def _row(db: sqlite3.Connection, table: str, claim_id: str) -> dict | None:
    row = db.execute(
        f"SELECT * FROM {table} WHERE claim_id = ?",  # noqa: S608
        (claim_id,),
    ).fetchone()
    return dict(row) if row else None


def _customer_name(db: sqlite3.Connection, customer_id: str) -> str:
    customer = _load(db, "customers", "customer_id", customer_id)
    return customer["name"] if customer else ""


def list_claims(db: sqlite3.Connection) -> list[ClaimSummary]:
    """Every claim in the queue, in claim id order."""
    rows = db.execute(
        "SELECT c.data, c.status, d.decision, d.payout FROM claims c "
        "LEFT JOIN decisions d ON d.claim_id = c.claim_id ORDER BY c.claim_id"
    ).fetchall()
    claims = []
    for row in rows:
        data = {**json.loads(row["data"]), "status": row["status"]}
        name = _customer_name(db, data["customer_id"])
        claims.append(
            ClaimSummary(
                **data,
                customer_name=name,
                decision=row["decision"],
                payout=row["payout"],
            )
        )
    return claims


def get_claim(db: sqlite3.Connection, claim_id: str) -> Claim | None:
    """One claim in full, with its decision, payment and sign-off if it has them."""
    row = db.execute(
        "SELECT data, status FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        return None
    data = json.loads(row["data"])
    decision, payment = _row(db, "decisions", claim_id), _row(db, "payments", claim_id)
    sign_off = _row(db, "sign_offs", claim_id)
    if sign_off:
        handler = _load(db, "handlers", "handler_id", sign_off["handler_id"])
        sign_off["handler_name"] = handler["name"] if handler else ""
    return Claim(
        **{**data, "status": row["status"]},
        customer_name=_customer_name(db, data["customer_id"]),
        decision=Decision(**decision) if decision else None,
        payment=Payment(**payment) if payment else None,
        sign_off=SignOff(**sign_off) if sign_off else None,
    )


def get_policy(db: sqlite3.Connection, policy_id: str) -> Policy | None:
    """One policy record."""
    data = _load(db, "policies", "policy_id", policy_id)
    return Policy(**data) if data else None


def get_claim_history(db: sqlite3.Connection, customer_id: str) -> ClaimHistory | None:
    """A customer's name and earlier claims, without their contact details."""
    data = _load(db, "customers", "customer_id", customer_id)
    return ClaimHistory(**data) if data else None


def list_handlers(db: sqlite3.Connection) -> list[Handler]:
    """Every claims handler."""
    rows = db.execute("SELECT data FROM handlers ORDER BY handler_id").fetchall()
    return [Handler(**json.loads(row["data"])) for row in rows]
