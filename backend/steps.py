"""The steps the agent takes on a claim."""

from sqlalchemy import Connection, insert, select

from backend import db, records
from backend.db import steps
from backend.models import Step, StepRequest


def add_step(conn: Connection, claim_id: str, request: StepRequest) -> Step:
    """Store one step of the agent's work."""
    records.status(conn, claim_id)
    created_at = db.now()
    step_id = conn.execute(
        insert(steps)
        .values(claim_id=claim_id, created_at=created_at, **request.model_dump())
        .returning(steps.c.id)
    ).scalar_one()
    conn.commit()
    return Step(
        **request.model_dump(),
        id=step_id,
        claim_id=claim_id,
        created_at=created_at,
    )


def list_steps(conn: Connection, claim_id: str) -> list[Step]:
    """Return a claim's steps, oldest first."""
    records.status(conn, claim_id)
    query = select(steps).where(steps.c.claim_id == claim_id).order_by(steps.c.id)
    return [Step(**row) for row in conn.execute(query).mappings()]
