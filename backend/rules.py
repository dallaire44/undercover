"""The rules: decisions, payments and sign-off.

A step of the agent can run again after a restart, so a repeat of a decision or a
payment already recorded counts as done and returns the claim.
"""

from sqlalchemy import Connection, insert, update

from backend import db, records
from backend.db import claims, decisions, payments, sign_offs
from backend.errors import Refused
from backend.models import (
    ClaimDetail,
    DecisionRecord,
    DecisionRequest,
    PaymentRequest,
    SignOff,
    SignOffRequest,
    State,
)
from backend.payouts import approval_limit


def set_status(conn: Connection, claim_id: str, state: State) -> None:
    """Move a claim to a new state."""
    conn.execute(
        update(claims).where(claims.c.claim_id == claim_id).values(status=state)
    )


def record_decision(
    conn: Connection, claim_id: str, request: DecisionRequest
) -> ClaimDetail:
    """Record the agent's decision and move the claim on, or confirm a repeat."""
    records.status(conn, claim_id)
    approved = request.decision == "approve"
    payout = round(request.payout, 2) if approved else 0.0
    found = records.one(conn, decisions, claim_id)
    if found:
        if (found["decision"], found["payout"]) != (request.decision, payout):
            raise Refused(f"{claim_id} already has a decision")
        return records.get_claim(conn, claim_id)
    decision = DecisionRecord(
        **{**request.model_dump(), "payout": payout}, decided_at=db.now()
    )
    if not approved:
        state = "decided"
    elif payout > approval_limit():
        state = "awaiting_sign_off"
    else:
        state = "in_progress"
    conn.execute(insert(decisions).values(claim_id=claim_id, **decision.model_dump()))
    set_status(conn, claim_id, state)
    conn.commit()
    return records.get_claim(conn, claim_id)


def pay_claim(conn: Connection, claim_id: str, request: PaymentRequest) -> ClaimDetail:
    """Pay an approved claim, once, for exactly its payout, or confirm a repeat."""
    records.status(conn, claim_id)
    decision = records.one(conn, decisions, claim_id)
    if decision is None or decision["decision"] != "approve":
        raise Refused(f"{claim_id} has no approved decision to pay")
    if round(request.amount, 2) != decision["payout"]:
        raise Refused(f"The approved payout is ${decision['payout']:,.2f}")
    if records.one(conn, payments, claim_id):
        return records.get_claim(conn, claim_id)
    signed = records.one(conn, sign_offs, claim_id)
    if decision["payout"] > approval_limit() and not signed:
        raise Refused(
            f"A payout over ${approval_limit():,.2f} needs a handler's sign-off"
        )
    by = records.signed_off(conn, signed) if signed else None
    conn.execute(
        insert(payments).values(
            claim_id=claim_id,
            amount=decision["payout"],
            paid_at=db.now(),
            signed_off_by=by.handler_name if by else None,
            signed_off_at=by.signed_at if by else None,
        )
    )
    set_status(conn, claim_id, "decided")
    conn.commit()
    return records.get_claim(conn, claim_id)


def sign_off(conn: Connection, claim_id: str, request: SignOffRequest) -> SignOff:
    """Record a handler's sign-off, so the agent can pick the claim up and pay it."""
    handler = records.document(conn, "handlers", request.handler_id)
    if records.claim_row(conn, claim_id)["copy_of"]:
        raise Refused("An evaluation's copy can't be signed off")
    if records.status(conn, claim_id) != "awaiting_sign_off":
        raise Refused(f"{claim_id} is not waiting for sign-off")
    signed = SignOff(
        handler_id=request.handler_id, handler_name=handler["name"], signed_at=db.now()
    )
    conn.execute(
        insert(sign_offs).values(
            claim_id=claim_id, handler_id=signed.handler_id, signed_at=signed.signed_at
        )
    )
    set_status(conn, claim_id, "in_progress")
    conn.commit()
    return signed
