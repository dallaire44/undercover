"""The agent's steps on a claim: what it said, which tool it called, what came back."""

import sqlite3
from datetime import UTC, datetime

from fastapi import HTTPException

from backend.models import Step, StepIn


def _require_claim(db: sqlite3.Connection, claim_id: str) -> None:
    if (
        db.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
        is None
    ):
        raise HTTPException(status_code=404, detail="Claim not found")


def add_step(db: sqlite3.Connection, claim_id: str, body: StepIn) -> Step:
    """Store one step and return it."""
    _require_claim(db, claim_id)
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    cursor = db.execute(
        "INSERT INTO steps (claim_id, thread_id, kind, text, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (claim_id, body.thread_id, body.kind, body.text, created_at),
    )
    db.commit()
    return Step(id=cursor.lastrowid or 0, created_at=created_at, **body.model_dump())


def list_steps(db: sqlite3.Connection, claim_id: str) -> list[Step]:
    """A claim's steps, oldest first."""
    _require_claim(db, claim_id)
    rows = db.execute(
        "SELECT id, thread_id, kind, text, created_at FROM steps "
        "WHERE claim_id = ? ORDER BY id",
        (claim_id,),
    ).fetchall()
    return [Step(**dict(row)) for row in rows]
