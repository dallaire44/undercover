"""Run the agent on claims, in the background."""

import sqlite3
import uuid
from contextlib import closing

from agent.main import run as run_agent
from backend import db, records, rules, steps
from backend.models import StepRequest


def note(conn: sqlite3.Connection, claim_id: str, thread_id: str, text: str) -> None:
    """Record a step written by the system, not by the agent."""
    steps.add_step(
        conn, claim_id, StepRequest(thread_id=thread_id, kind="message", text=text)
    )


def start(conn: sqlite3.Connection, claim_id: str) -> None:
    """Move a waiting claim to in progress, or refuse."""
    if records.status(conn, claim_id) != "waiting":
        raise rules.conflict(f"{claim_id} is not waiting")
    with conn:
        rules.set_status(conn, claim_id, "in_progress")


def waiting_ids(conn: sqlite3.Connection) -> list[str]:
    """Return the ids of the claims waiting in the queue."""
    rows = conn.execute(
        "SELECT claim_id FROM claims WHERE status = 'waiting' ORDER BY claim_id"
    )
    return [row["claim_id"] for row in rows]


def run_claim(claim_id: str) -> None:
    """Run the agent on a claim that is in progress. Without a decision, put it back."""
    thread_id = str(uuid.uuid4())
    with closing(db.connect()) as conn:
        note(conn, claim_id, thread_id, "Agent started")
        problem = None
        try:
            run_agent(claim_id, thread_id)
        except Exception as error:  # noqa: BLE001
            problem = f"The agent failed: {error}"
        if problem is None and records.one(conn, "decisions", claim_id):
            note(conn, claim_id, thread_id, "Agent finished")
            return
        note(
            conn,
            claim_id,
            thread_id,
            problem or "The agent finished without a decision",
        )
        with conn:
            rules.set_status(conn, claim_id, "waiting")


def run_queue(claim_ids: list[str]) -> None:
    """Run the agent on each of these claims in turn, if it is still waiting."""
    for claim_id in claim_ids:
        with closing(db.connect()) as conn:
            if records.status(conn, claim_id) != "waiting":
                continue
            start(conn, claim_id)
        run_claim(claim_id)
