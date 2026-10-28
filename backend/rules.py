"""Decisions, payments and sign-offs, and the rules that guard them."""

import json
import sqlite3
from datetime import UTC, datetime

from fastapi import HTTPException

from backend.db import DATA
from backend.models import DecisionIn

LIMIT = json.loads((DATA / "company.json").read_text())["payout_approval_limit"]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _begin(db: sqlite3.Connection, claim_id: str) -> str:
    """Take the write lock and return the claim's status, or answer 404."""
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        "SELECT status FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return row["status"]


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def _set_status(db: sqlite3.Connection, claim_id: str, status: str) -> None:
    db.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id))


def _pay(db: sqlite3.Connection, claim_id: str, amount: float) -> None:
    db.execute("INSERT INTO payments VALUES (?, ?, ?)", (claim_id, amount, _now()))
    _set_status(db, claim_id, "decided")


def record_decision(db: sqlite3.Connection, claim_id: str, body: DecisionIn) -> None:
    """Record the decision. Declines and referrals pay nothing and finish the claim."""
    _begin(db, claim_id)
    if db.execute("SELECT 1 FROM decisions WHERE claim_id = ?", (claim_id,)).fetchone():
        raise _conflict("This claim already has a decision")
    approved = body.decision == "approve"
    payout = round(body.payout, 2) if approved else 0.0
    if not approved:
        status = "decided"
    elif payout > LIMIT:
        status = "awaiting_sign_off"
    else:
        status = "in_progress"
    db.execute(
        "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
        (claim_id, body.decision, payout, body.reason, body.policy_section, _now()),
    )
    _set_status(db, claim_id, status)
    db.commit()


def pay_claim(db: sqlite3.Connection, claim_id: str, amount: float) -> None:
    """Pay an approved claim, once, for exactly the approved payout."""
    _begin(db, claim_id)
    decision = db.execute(
        "SELECT decision, payout FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if decision is None:
        raise _conflict("The claim has no decision")
    if decision["decision"] != "approve":
        raise _conflict("Only an approved claim can be paid")
    if db.execute("SELECT 1 FROM payments WHERE claim_id = ?", (claim_id,)).fetchone():
        raise _conflict("The claim is already paid")
    if round(amount, 2) != decision["payout"]:
        raise _conflict("The amount is not the approved payout")
    if decision["payout"] > LIMIT:
        raise _conflict(f"A payout over ${LIMIT:,.2f} needs a handler's sign-off")
    _pay(db, claim_id, decision["payout"])
    db.commit()


def sign_off(db: sqlite3.Connection, claim_id: str, handler_id: str) -> None:
    """A handler signs off an approved payout over the limit, which pays it."""
    status = _begin(db, claim_id)
    handler = db.execute(
        "SELECT 1 FROM handlers WHERE handler_id = ?", (handler_id,)
    ).fetchone()
    if handler is None:
        raise HTTPException(status_code=404, detail="Handler not found")
    if status != "awaiting_sign_off":
        raise _conflict("The claim is not waiting for sign-off")
    payout = db.execute(
        "SELECT payout FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()["payout"]
    db.execute("INSERT INTO sign_offs VALUES (?, ?, ?)", (claim_id, handler_id, _now()))
    _pay(db, claim_id, payout)
    db.commit()
