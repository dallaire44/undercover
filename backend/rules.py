"""The rules: decisions, payments and sign-off."""

import sqlite3
from datetime import UTC, datetime

from fastapi import HTTPException

from backend import db, records
from backend.models import (
    DecisionRecord,
    DecisionRequest,
    Payment,
    PaymentRequest,
    SignOff,
    SignOffRequest,
)


def now() -> str:
    """Return the current time, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def approval_limit() -> float:
    """Return the payout above which a handler must sign off."""
    return db.load("company")["payout_approval_limit"]


def set_status(conn: sqlite3.Connection, claim_id: str, state: str) -> None:
    """Move a claim to a new state."""
    conn.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (state, claim_id))


def conflict(message: str) -> HTTPException:
    """Return the error for a request the rules refuse."""
    return HTTPException(409, message)


def record_decision(
    conn: sqlite3.Connection, claim_id: str, request: DecisionRequest
) -> DecisionRecord:
    """Record the agent's decision and move the claim on."""
    records.status(conn, claim_id)
    if records.one(conn, "decisions", claim_id):
        raise conflict(f"{claim_id} already has a decision")
    approved = request.decision == "approve"
    payout = request.payout if approved else 0.0
    decision = DecisionRecord(
        **{**request.model_dump(), "payout": payout}, decided_at=now()
    )
    if not approved:
        state = "decided"
    elif payout > approval_limit():
        state = "awaiting_sign_off"
    else:
        state = "in_progress"
    with conn:
        conn.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
            (claim_id, *decision.model_dump().values()),
        )
        set_status(conn, claim_id, state)
    return decision


def pay_claim(
    conn: sqlite3.Connection, claim_id: str, request: PaymentRequest
) -> Payment:
    """Pay an approved claim, once, for exactly its payout."""
    records.status(conn, claim_id)
    decision = records.one(conn, "decisions", claim_id)
    if decision is None or decision["decision"] != "approve":
        raise conflict(f"{claim_id} has no approved decision to pay")
    if records.one(conn, "payments", claim_id):
        raise conflict(f"{claim_id} is already paid")
    if round(request.amount, 2) != decision["payout"]:
        raise conflict(f"The approved payout is ${decision['payout']:,.2f}")
    if decision["payout"] > approval_limit() and not records.one(
        conn, "sign_offs", claim_id
    ):
        raise conflict(
            f"A payout over ${approval_limit():,.2f} needs a handler's sign-off"
        )
    return release(conn, claim_id, decision["payout"])


def release(conn: sqlite3.Connection, claim_id: str, amount: float) -> Payment:
    """Record the payment and finish the claim."""
    payment = Payment(amount=amount, paid_at=now())
    with conn:
        conn.execute(
            "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, amount, payment.paid_at)
        )
        set_status(conn, claim_id, "decided")
    return payment


def sign_off(
    conn: sqlite3.Connection, claim_id: str, request: SignOffRequest
) -> SignOff:
    """Record a handler's sign-off, release the payment and finish the claim."""
    handler = records.document(conn, "handlers", "handler_id", request.handler_id)
    if records.status(conn, claim_id) != "awaiting_sign_off":
        raise conflict(f"{claim_id} is not waiting for sign-off")
    query = "SELECT payout FROM decisions WHERE claim_id = ?"
    payout = conn.execute(query, (claim_id,)).fetchone()["payout"]
    signed = SignOff(
        handler_id=request.handler_id, handler_name=handler["name"], signed_at=now()
    )
    with conn:
        conn.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)",
            (claim_id, signed.handler_id, signed.signed_at),
        )
    release(conn, claim_id, payout)
    return signed
