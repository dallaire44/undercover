"""Runs of the agent over the queue: the cap, the to-do list and failed attempts."""

import uuid

from sqlalchemy import Connection, RowMapping, delete, func, insert, select, update

from backend import db, records, steps
from backend.db import claims, runs, todos
from backend.errors import NotFound, Refused
from backend.models import ClaimSummary, Run, RunState, State, StepRequest, Todo

MAX_ATTEMPTS = 2
RESTARTED = "The backend restarted during the run."


def start(conn: Connection, cap: int) -> Run:
    """Start a run capped at `cap` claims, unless one is already running."""
    if conn.execute(select(runs).where(runs.c.status == "running")).first():
        raise Refused("A run is already running")
    count = conn.execute(select(func.count()).select_from(runs)).scalar_one()
    run_id = f"RUN-{count + 1:04d}"
    conn.execute(
        insert(runs).values(
            run_id=run_id, cap=cap, status="running", summary="", started_at=db.now()
        )
    )
    conn.commit()
    return get(conn, run_id)


def row(conn: Connection, run_id: str) -> RowMapping:
    """Return a run's row, or raise 404."""
    found = conn.execute(select(runs).where(runs.c.run_id == run_id)).mappings()
    first = found.first()
    if first is None:
        raise NotFound(f"{run_id} not found")
    return first


def running(conn: Connection, run_id: str) -> RowMapping:
    """Return a run's row if it is running, or refuse."""
    found = row(conn, run_id)
    if found["status"] != "running":
        raise Refused(f"{run_id} is {found['status']}")
    return found


def claim_ids(conn: Connection, run_id: str, state: State | None = None) -> list[str]:
    """Return the ids of the run's claims, optionally only those in one state."""
    query = select(claims.c.claim_id).where(claims.c.run_id == run_id)
    if state:
        query = query.where(claims.c.status == state)
    return list(conn.scalars(query.order_by(claims.c.claim_id)))


def get(conn: Connection, run_id: str) -> Run:
    """Return a run with its claims and its to-do list."""
    query = (
        select(todos.c.content, todos.c.status)
        .where(todos.c.run_id == run_id)
        .order_by(todos.c.position)
    )
    return Run(
        **row(conn, run_id),
        claim_ids=claim_ids(conn, run_id),
        todos=[Todo(**todo) for todo in conn.execute(query).mappings()],
    )


def latest(conn: Connection) -> Run | None:
    """Return the latest run, or None before the first."""
    query = select(runs.c.run_id).order_by(runs.c.run_id.desc()).limit(1)
    found = conn.scalar(query)
    return get(conn, found) if found else None


def claims_to_work(conn: Connection, run_id: str) -> list[ClaimSummary]:
    """Return the waiting claims the run may work: its own, and others under its cap."""
    query = select(claims.c.claim_id).where(claims.c.status == "waiting")
    if len(claim_ids(conn, run_id)) >= row(conn, run_id)["cap"]:
        query = query.where(claims.c.run_id == run_id)
    ids = set(conn.scalars(query))
    return [c for c in records.list_claims(conn) if c.claim_id in ids]


def take_claim(conn: Connection, run_id: str, claim_id: str) -> ClaimSummary:
    """Move a waiting claim into the run and in progress, within the run's cap."""
    run = running(conn, run_id)
    if records.status(conn, claim_id) != "waiting":
        raise Refused(f"{claim_id} is not waiting")
    if claim_id not in {c.claim_id for c in claims_to_work(conn, run_id)}:
        raise Refused(f"The run's cap of {run['cap']} claims is reached")
    conn.execute(
        update(claims)
        .where(claims.c.claim_id == claim_id)
        .values(status="in_progress", run_id=run_id, thread_id=str(uuid.uuid4()))
    )
    conn.commit()
    return records.summary(conn, claim_id)


def return_claim(
    conn: Connection, claim_id: str, thread_id: str, reason: str
) -> ClaimSummary:
    """After a failed attempt, return the claim to the queue or to a handler."""
    found = records.claim_row(conn, claim_id)
    if found["status"] != "in_progress":
        raise Refused(f"{claim_id} is not in progress")
    attempts = found["attempts"] + 1
    if attempts < MAX_ATTEMPTS:
        state, outcome = "waiting", f"Back in the queue after attempt {attempts}."
    else:
        state, outcome = (
            "needs_handler",
            f"Left for a handler after {attempts} attempts.",
        )
    conn.execute(
        update(claims)
        .where(claims.c.claim_id == claim_id)
        .values(status=state, attempts=attempts, thread_id=None)
    )
    conn.commit()
    text = f"{reason}\n{outcome}"
    step = StepRequest(thread_id=thread_id, kind="message", text=text)
    steps.add_step(conn, claim_id, step)
    return records.summary(conn, claim_id)


def write_todos(conn: Connection, run_id: str, items: list[Todo]) -> list[Todo]:
    """Replace the run's to-do list."""
    running(conn, run_id)
    conn.execute(delete(todos).where(todos.c.run_id == run_id))
    if items:
        rows = [
            {"run_id": run_id, "position": i, **todo.model_dump()}
            for i, todo in enumerate(items)
        ]
        conn.execute(insert(todos), rows)
    conn.commit()
    return items


def close(conn: Connection, run_id: str, state: RunState, summary: str) -> Run:
    """Mark the run finished or stopped, with its summary."""
    conn.execute(
        update(runs)
        .where(runs.c.run_id == run_id)
        .values(status=state, summary=summary, finished_at=db.now())
    )
    conn.commit()
    return get(conn, run_id)


def finish(conn: Connection, run_id: str, summary: str) -> Run:
    """Finish the run, unless a claim is in progress or still to work."""
    running(conn, run_id)
    working = claim_ids(conn, run_id, "in_progress")
    if working:
        raise Refused(f"Still in progress: {', '.join(working)}")
    missed = [c.claim_id for c in claims_to_work(conn, run_id)]
    if missed:
        raise Refused(f"Still to work within the cap: {', '.join(missed)}")
    return close(conn, run_id, "finished", summary)


def stop(conn: Connection, run_id: str, reason: str) -> Run:
    """Stop the run, returning each claim it had in progress."""
    for claim_id in claim_ids(conn, run_id, "in_progress"):
        return_claim(conn, claim_id, thread_id=run_id, reason=reason)
    return close(conn, run_id, "stopped", reason)


def recover(conn: Connection) -> None:
    """Stop every run left running when the backend last stopped."""
    query = select(runs.c.run_id).where(runs.c.status == "running")
    for run_id in conn.scalars(query).all():
        stop(conn, run_id, RESTARTED)
