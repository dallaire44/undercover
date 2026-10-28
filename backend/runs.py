"""Running the agent on claims, in the background."""

import uuid

from agent.main import run as agent_run
from backend.db import connect
from backend.models import StepIn
from backend.steps import add_step


def start(claim_id: str) -> bool:
    """Move a waiting claim to in progress. False if it isn't waiting."""
    db = connect()
    cursor = db.execute(
        "UPDATE claims SET status = 'in_progress' "
        "WHERE claim_id = ? AND status = 'waiting'",
        (claim_id,),
    )
    db.commit()
    db.close()
    return cursor.rowcount == 1


def waiting_claims() -> list[str]:
    """The ids of the claims still waiting, in order."""
    db = connect()
    rows = db.execute(
        "SELECT claim_id FROM claims WHERE status = 'waiting' ORDER BY claim_id"
    ).fetchall()
    db.close()
    return [row["claim_id"] for row in rows]


def work_claim(claim_id: str) -> None:
    """Run the agent on a claim that is in progress, and record how it went."""
    thread_id = uuid.uuid4().hex
    db = connect()

    def note(text: str) -> None:
        add_step(db, claim_id, StepIn(thread_id=thread_id, kind="message", text=text))

    note("Agent started")
    problem = None
    try:
        agent_run(claim_id, thread_id)
    except Exception as error:
        problem = f"Agent failed: {error}"
    has_decision = db.execute(
        "SELECT 1 FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if not has_decision:
        problem = problem or "Agent finished without a decision"
        note(problem)
        db.execute(
            "UPDATE claims SET status = 'waiting' WHERE claim_id = ?", (claim_id,)
        )
        db.commit()
    note("Agent finished")
    db.close()


def work_queue() -> None:
    """Work through every waiting claim, one after another."""
    for claim_id in waiting_claims():
        if start(claim_id):
            work_claim(claim_id)
