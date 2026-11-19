"""What the agent uses on each claim: its model calls, and its time at work."""

from sqlalchemy import Connection, insert

from backend import db, records
from backend.db import model_calls, work_times
from backend.models import ModelCall, ModelCallRequest, WorkTime, WorkTimeRequest


def record_model_call(
    conn: Connection, claim_id: str, request: ModelCallRequest
) -> ModelCall:
    """Store one model call's tokens and cost, with the run it happened in."""
    records.status(conn, claim_id)
    called_at = db.now()
    call_id = conn.execute(
        insert(model_calls)
        .values(claim_id=claim_id, called_at=called_at, **request.model_dump())
        .returning(model_calls.c.id)
    ).scalar_one()
    conn.commit()
    return ModelCall(
        **request.model_dump(), id=call_id, claim_id=claim_id, called_at=called_at
    )


def record_work_time(
    conn: Connection, claim_id: str, request: WorkTimeRequest
) -> WorkTime:
    """Store one stretch of the agent's work on a claim, with the run it was in."""
    records.status(conn, claim_id)
    time_id = conn.execute(
        insert(work_times)
        .values(claim_id=claim_id, **request.model_dump())
        .returning(work_times.c.id)
    ).scalar_one()
    conn.commit()
    return WorkTime(**request.model_dump(), id=time_id, claim_id=claim_id)
