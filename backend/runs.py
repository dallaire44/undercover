"""Runs of the agent over the queue: the cap, the to-do list and failed attempts."""

import sqlite3

from backend import db, records, steps
from backend.errors import NotFound, Refused
from backend.models import ClaimSummary, Run, RunState, State, StepRequest, Todo

MAX_ATTEMPTS = 2
RESTARTED = "The backend restarted during the run."


def start(conn: sqlite3.Connection, cap: int) -> Run:
    """Start a run capped at `cap` claims, unless one is already running."""
    if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
        raise Refused("A run is already running")
    count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    run_id = f"RUN-{count + 1:04d}"
    with conn:
        conn.execute(
            "INSERT INTO runs VALUES (?, ?, 'running', '', ?, NULL)",
            (run_id, cap, db.now()),
        )
    return get(conn, run_id)


def row(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    """Return a run's row, or raise 404."""
    found = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if found is None:
        raise NotFound(f"{run_id} not found")
    return found


def running(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    """Return a run's row if it is running, or refuse."""
    found = row(conn, run_id)
    if found["status"] != "running":
        raise Refused(f"{run_id} is {found['status']}")
    return found


def claim_ids(
    conn: sqlite3.Connection, run_id: str, state: State | None = None
) -> list[str]:
    """Return the ids of the run's claims, optionally only those in one state."""
    rows = conn.execute(
        "SELECT claim_id FROM claims WHERE run_id = :run_id "
        "AND (:state IS NULL OR status = :state) ORDER BY claim_id",
        {"run_id": run_id, "state": state},
    )
    return [r["claim_id"] for r in rows]


def get(conn: sqlite3.Connection, run_id: str) -> Run:
    """Return a run with its claims and its to-do list."""
    todos = conn.execute(
        "SELECT content, status FROM todos WHERE run_id = ? ORDER BY position",
        (run_id,),
    )
    return Run(
        **row(conn, run_id),
        claim_ids=claim_ids(conn, run_id),
        todos=[Todo(**todo) for todo in todos],
    )


def latest(conn: sqlite3.Connection) -> Run | None:
    """Return the latest run, or None before the first."""
    found = conn.execute("SELECT run_id FROM runs ORDER BY rowid DESC").fetchone()
    return get(conn, found["run_id"]) if found else None


def claims_to_work(conn: sqlite3.Connection, run_id: str) -> list[ClaimSummary]:
    """Return the waiting claims the run may work: its own, and others under its cap."""
    under_cap = len(claim_ids(conn, run_id)) < row(conn, run_id)["cap"]
    rows = conn.execute(
        "SELECT claim_id FROM claims WHERE status = 'waiting' AND (run_id = ? OR ?)",
        (run_id, under_cap),
    )
    ids = {r["claim_id"] for r in rows}
    return [c for c in records.list_claims(conn) if c.claim_id in ids]


def take_claim(conn: sqlite3.Connection, run_id: str, claim_id: str) -> ClaimSummary:
    """Move a waiting claim into the run and in progress, within the run's cap."""
    run = running(conn, run_id)
    if records.status(conn, claim_id) != "waiting":
        raise Refused(f"{claim_id} is not waiting")
    if claim_id not in {c.claim_id for c in claims_to_work(conn, run_id)}:
        raise Refused(f"The run's cap of {run['cap']} claims is reached")
    with conn:
        conn.execute(
            "UPDATE claims SET status = 'in_progress', run_id = ? WHERE claim_id = ?",
            (run_id, claim_id),
        )
    return records.summary(conn, claim_id)


def return_claim(
    conn: sqlite3.Connection, claim_id: str, thread_id: str, reason: str
) -> ClaimSummary:
    """After a failed attempt, return the claim to the queue or to a handler."""
    row = records.claim_row(conn, claim_id)
    if row["status"] != "in_progress":
        raise Refused(f"{claim_id} is not in progress")
    attempts = row["attempts"] + 1
    if attempts < MAX_ATTEMPTS:
        state, outcome = "waiting", f"Back in the queue after attempt {attempts}."
    else:
        state, outcome = (
            "needs_handler",
            f"Left for a handler after {attempts} attempts.",
        )
    with conn:
        conn.execute(
            "UPDATE claims SET status = ?, attempts = ? WHERE claim_id = ?",
            (state, attempts, claim_id),
        )
    text = f"{reason}\n{outcome}"
    step = StepRequest(thread_id=thread_id, kind="message", text=text)
    steps.add_step(conn, claim_id, step)
    return records.summary(conn, claim_id)


def write_todos(conn: sqlite3.Connection, run_id: str, todos: list[Todo]) -> list[Todo]:
    """Replace the run's to-do list."""
    running(conn, run_id)
    with conn:
        conn.execute("DELETE FROM todos WHERE run_id = ?", (run_id,))
        conn.executemany(
            "INSERT INTO todos VALUES (?, ?, ?, ?)",
            [(run_id, i, t.content, t.status) for i, t in enumerate(todos)],
        )
    return todos


def close(conn: sqlite3.Connection, run_id: str, state: RunState, summary: str) -> Run:
    """Mark the run finished or stopped, with its summary."""
    with conn:
        conn.execute(
            "UPDATE runs SET status = ?, summary = ?, finished_at = ? WHERE run_id = ?",
            (state, summary, db.now(), run_id),
        )
    return get(conn, run_id)


def finish(conn: sqlite3.Connection, run_id: str, summary: str) -> Run:
    """Finish the run, unless a claim is in progress or still to work."""
    running(conn, run_id)
    working = claim_ids(conn, run_id, "in_progress")
    if working:
        raise Refused(f"Still in progress: {', '.join(working)}")
    missed = [c.claim_id for c in claims_to_work(conn, run_id)]
    if missed:
        raise Refused(f"Still to work within the cap: {', '.join(missed)}")
    return close(conn, run_id, "finished", summary)


def stop(conn: sqlite3.Connection, run_id: str, reason: str) -> Run:
    """Stop the run, returning each claim it had in progress."""
    for claim_id in claim_ids(conn, run_id, "in_progress"):
        return_claim(conn, claim_id, thread_id=run_id, reason=reason)
    return close(conn, run_id, "stopped", reason)


def recover(conn: sqlite3.Connection) -> None:
    """Stop every run left running when the backend last stopped."""
    rows = conn.execute("SELECT run_id FROM runs WHERE status = 'running'")
    for found in rows.fetchall():
        stop(conn, found["run_id"], RESTARTED)
