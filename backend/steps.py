"""The steps the agent takes on a claim."""

import sqlite3

from backend import records, rules
from backend.models import Step, StepRequest


def add_step(conn: sqlite3.Connection, claim_id: str, request: StepRequest) -> Step:
    """Store one step of the agent's work."""
    records.status(conn, claim_id)
    created_at = rules.now()
    with conn:
        cursor = conn.execute(
            """INSERT INTO steps (claim_id, thread_id, kind, text, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (claim_id, request.thread_id, request.kind, request.text, created_at),
        )
    return Step(
        **request.model_dump(),
        id=cursor.lastrowid or 0,
        claim_id=claim_id,
        created_at=created_at,
    )


def list_steps(conn: sqlite3.Connection, claim_id: str) -> list[Step]:
    """Return a claim's steps, oldest first."""
    records.status(conn, claim_id)
    rows = conn.execute(
        "SELECT * FROM steps WHERE claim_id = ? ORDER BY id", (claim_id,)
    )
    return [Step(**row) for row in rows]
