"""Read the records: claims, policies, customers and handlers."""

from typing import Any

from sqlalchemy import ColumnElement, Connection, RowMapping, Table, select

from backend import db
from backend.db import claims, customers, decisions
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

CLAIMS = (
    select(
        claims.c.status,
        claims.c.attempts,
        claims.c.run_id,
        claims.c.thread_id,
        claims.c.doc,
        decisions.c.decision,
        decisions.c.payout,
        customers.c.doc["name"].as_string().label("customer_name"),
    )
    .join(customers, customers.c.customer_id == claims.c.doc["customer_id"].as_string())
    .outerjoin(decisions, decisions.c.claim_id == claims.c.claim_id)
    .order_by(claims.c.claim_id)
)


def document(conn: Connection, table: str, value: str) -> dict[str, Any]:
    """Return one stored claim, policy, customer or handler, or raise NotFound."""
    found = db.DOCUMENTS[table]
    key = next(iter(found.primary_key))
    doc = conn.execute(select(found.c.doc).where(key == value)).scalar()
    if doc is None:
        raise NotFound(f"{value} not found")
    return doc


def one(conn: Connection, table: Table, claim_id: str) -> RowMapping | None:
    """Return a claim's row in one of the tables keyed by claim id."""
    query = select(table).where(table.c.claim_id == claim_id)
    return conn.execute(query).mappings().first()


def claim_row(conn: Connection, claim_id: str) -> RowMapping:
    """Return a claim's state, attempts and record, or raise NotFound."""
    row = one(conn, claims, claim_id)
    if row is None:
        raise NotFound(f"{claim_id} not found")
    return row


def status(conn: Connection, claim_id: str) -> State:
    """Return a claim's state, or raise NotFound."""
    return claim_row(conn, claim_id)["status"]


def summaries(conn: Connection, *where: ColumnElement[bool]) -> list[ClaimSummary]:
    """Return the claims that match, as they show in the queue."""
    query = CLAIMS.where(*where)
    return [
        ClaimSummary(
            **{**row["doc"], "status": row["status"]},
            attempts=row["attempts"],
            run_id=row["run_id"],
            thread_id=row["thread_id"],
            customer_name=row["customer_name"],
            decision=row["decision"],
            payout=row["payout"],
        )
        for row in conn.execute(query).mappings()
    ]


def list_claims(conn: Connection) -> list[ClaimSummary]:
    """Return every claim in the queue, with its decision and payout if any."""
    return summaries(conn)


def in_run(conn: Connection, run_id: str) -> list[ClaimSummary]:
    """Return the claims a run has worked, as they show in the queue."""
    return summaries(conn, claims.c.run_id == run_id)


def summary(conn: Connection, claim_id: str) -> ClaimSummary:
    """Return one claim, known to exist, as it shows in the queue."""
    (found,) = summaries(conn, claims.c.claim_id == claim_id)
    return found


def signed_off(conn: Connection, row: RowMapping) -> SignOff:
    """Return a sign-off with the handler's name."""
    handler = document(conn, "handlers", row["handler_id"])
    return SignOff(**row, handler_name=handler["name"])


def get_claim(conn: Connection, claim_id: str) -> ClaimDetail:
    """Return one claim in full, with its decision, payment and sign-off."""
    row = claim_row(conn, claim_id)
    claim = row["doc"]
    customer = document(conn, "customers", claim["customer_id"])
    decision, payment, sign_off = (
        one(conn, t, claim_id) for t in (decisions, db.payments, db.sign_offs)
    )
    return ClaimDetail(
        **{**claim, "status": row["status"]},
        attempts=row["attempts"],
        run_id=row["run_id"],
        thread_id=row["thread_id"],
        customer_name=customer["name"],
        decision=DecisionRecord(**decision) if decision else None,
        payment=Payment(**payment) if payment else None,
        sign_off=signed_off(conn, sign_off) if sign_off else None,
    )


def get_policy(conn: Connection, policy_id: str) -> Policy:
    """Return a policy with the name of its plan."""
    policy = document(conn, "policies", policy_id)
    plans = {p["plan"]: p["name"] for p in db.load("plans")["plans"]}
    return Policy(**policy, plan_name=plans[policy["plan"]])


def get_history(conn: Connection, customer_id: str) -> CustomerHistory:
    """Return a customer's name and earlier claims, with no contact details."""
    return CustomerHistory(**document(conn, "customers", customer_id))


def list_handlers(conn: Connection) -> list[Handler]:
    """Return the claims handlers."""
    query = select(db.handlers.c.doc).order_by(db.handlers.c.handler_id)
    return [Handler(**doc) for doc in conn.scalars(query)]
