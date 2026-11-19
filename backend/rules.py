"""The rules: decisions, payments and sign-off."""

from sqlalchemy import Connection, insert, select, update

from backend import db, records
from backend.db import claims, decisions, payments, sign_offs
from backend.errors import Refused
from backend.models import (
    DecisionRecord,
    DecisionRequest,
    Payment,
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
) -> DecisionRecord:
    """Record the agent's decision and move the claim on."""
    records.status(conn, claim_id)
    if records.one(conn, decisions, claim_id):
        raise Refused(f"{claim_id} already has a decision")
    approved = request.decision == "approve"
    payout = request.payout if approved else 0.0
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
    return decision


def pay_claim(conn: Connection, claim_id: str, request: PaymentRequest) -> Payment:
    """Pay an approved claim, once, for exactly its payout."""
    records.status(conn, claim_id)
    decision = records.one(conn, decisions, claim_id)
    if decision is None or decision["decision"] != "approve":
        raise Refused(f"{claim_id} has no approved decision to pay")
    if records.one(conn, payments, claim_id):
        raise Refused(f"{claim_id} is already paid")
    if round(request.amount, 2) != decision["payout"]:
        raise Refused(f"The approved payout is ${decision['payout']:,.2f}")
    if decision["payout"] > approval_limit() and not records.one(
        conn, sign_offs, claim_id
    ):
        raise Refused(
            f"A payout over ${approval_limit():,.2f} needs a handler's sign-off"
        )
    return release(conn, claim_id, decision["payout"])


def release(conn: Connection, claim_id: str, amount: float) -> Payment:
    """Record the payment and finish the claim."""
    payment = Payment(amount=amount, paid_at=db.now())
    conn.execute(insert(payments).values(claim_id=claim_id, **payment.model_dump()))
    set_status(conn, claim_id, "decided")
    conn.commit()
    return payment


def sign_off(conn: Connection, claim_id: str, request: SignOffRequest) -> SignOff:
    """Record a handler's sign-off, release the payment and finish the claim."""
    handler = records.document(conn, "handlers", request.handler_id)
    if records.status(conn, claim_id) != "awaiting_sign_off":
        raise Refused(f"{claim_id} is not waiting for sign-off")
    query = select(decisions.c.payout).where(decisions.c.claim_id == claim_id)
    payout = conn.execute(query).scalar_one()
    signed = SignOff(
        handler_id=request.handler_id, handler_name=handler["name"], signed_at=db.now()
    )
    conn.execute(
        insert(sign_offs).values(
            claim_id=claim_id, handler_id=signed.handler_id, signed_at=signed.signed_at
        )
    )
    release(conn, claim_id, payout)
    return signed
