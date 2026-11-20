"""Runs: dispatches of the queue, the claims they work, and failed attempts."""

import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, RowMapping, func, insert, select, update

from backend import db, records, steps, usage
from backend.db import claims, runs
from backend.errors import NotFound, Refused
from backend.models import (
    ClaimSummary,
    DispatchRequest,
    HeldPayout,
    Run,
    RunClaim,
    RunKind,
    RunState,
    RunSummary,
    State,
    StepRequest,
)

MAX_ATTEMPTS = 2
BUSY = "A dispatch or evaluation is already running"


def create(conn: Connection, values: dict[str, Any]) -> str:
    """Add a running run, unless one is already running, and return its id."""
    if conn.execute(select(runs.c.run_id).where(runs.c.status == "running")).first():
        raise Refused(BUSY)
    count = conn.execute(select(func.count()).select_from(runs)).scalar_one()
    run_id = f"RUN-{count + 1:04d}"
    conn.execute(
        insert(runs).values(
            run_id=run_id, status="running", started_at=db.now(), **values
        )
    )
    return run_id


def create_dispatch(conn: Connection, request: DispatchRequest) -> Run:
    """Create a dispatch of the queue with N claim agents at once."""
    values = {"kind": "dispatch", "claim_set": "queue", "tiny": False}
    run_id = create(conn, {**values, **request.model_dump()})
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


def summarize(worked: list[ClaimSummary]) -> RunSummary:
    """Sum up a run's claims from the records, with no model."""
    decided = Counter(c.decision for c in worked)
    return RunSummary(
        approved=decided["approve"],
        declined=decided["decline"],
        referred=decided["refer"],
        awaiting_sign_off=[
            HeldPayout(claim_id=c.claim_id, payout=c.payout or 0.0)
            for c in worked
            if c.status == "awaiting_sign_off"
        ],
        needs_handler=[c.claim_id for c in worked if c.status == "needs_handler"],
        in_progress=[c.claim_id for c in worked if c.status == "in_progress"],
    )


def seconds_since(started_at: str, finished_at: str | None) -> float:
    """Return the seconds from a run's start to its finish, or to now."""
    end = datetime.fromisoformat(finished_at) if finished_at else datetime.now(UTC)
    return (end - datetime.fromisoformat(started_at)).total_seconds()


def with_usage(claim: ClaimSummary, used: dict[str, tuple[float, float]]) -> RunClaim:
    """Add a claim's model cost and working time in the run."""
    cost, seconds = used.get(claim.claim_id, (0.0, 0.0))
    return RunClaim(**claim.model_dump(), cost=cost, seconds=seconds)


def get(conn: Connection, run_id: str) -> Run:
    """Return a run with its claims, its summary, its model cost and its time."""
    found = row(conn, run_id)
    worked = records.in_run(conn, run_id)
    used = usage.per_claim(conn, run_id)
    return Run(
        **found,
        claims=[with_usage(c, used) for c in worked],
        summary=summarize(worked),
        cost=usage.run_cost(conn, run_id),
        seconds=seconds_since(found["started_at"], found["finished_at"]),
    )


def ids_of(conn: Connection, *kinds: RunKind) -> list[str]:
    """Return the ids of the runs of the kinds given, newest first."""
    query = select(runs.c.run_id).where(runs.c.kind.in_(kinds))
    return list(conn.scalars(query.order_by(runs.c.run_id.desc())))


def latest(conn: Connection, *kinds: RunKind) -> Run | None:
    """Return the latest run of the kinds given, or None before the first."""
    found = ids_of(conn, *kinds)
    return get(conn, found[0]) if found else None


def claims_to_work(conn: Connection, run_id: str) -> list[ClaimSummary]:
    """Return the claims a run still has to work: in progress first, then waiting.

    A dispatch works the queue, and an evaluation its own copies. Each group is
    oldest submitted first.
    """
    if row(conn, run_id)["kind"] == "dispatch":
        found = records.list_claims(conn)
    else:
        found = records.in_run(conn, run_id)
    left = [c for c in found if c.status in ("in_progress", "waiting")]
    return sorted(
        left, key=lambda c: (c.status != "in_progress", c.submitted_on, c.claim_id)
    )


def take_claim(conn: Connection, run_id: str, claim_id: str) -> ClaimSummary:
    """Move a claim into the run, in progress.

    A waiting claim gets a new thread. One in progress keeps its thread, so it
    carries on from its last step as the same attempt.
    """
    running(conn, run_id)
    found = {c.claim_id: c for c in claims_to_work(conn, run_id)}.get(claim_id)
    if found is None:
        raise Refused(f"{claim_id} is not a claim this run can work")
    thread_id = found.thread_id or str(uuid.uuid4())
    conn.execute(
        update(claims)
        .where(claims.c.claim_id == claim_id)
        .values(status="in_progress", run_id=run_id, thread_id=thread_id)
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


def close(conn: Connection, run_id: str, state: RunState, reason: str | None) -> Run:
    """Mark the run finished, or stopped with its reason."""
    conn.execute(
        update(runs)
        .where(runs.c.run_id == run_id)
        .values(status=state, reason=reason, finished_at=db.now())
    )
    conn.commit()
    return get(conn, run_id)


def ids_in(conn: Connection, run_id: str, state: State) -> list[str]:
    """Return the ids of the run's claims in one state."""
    return [c.claim_id for c in records.in_run(conn, run_id) if c.status == state]


def finish(conn: Connection, run_id: str) -> Run:
    """Finish the run, unless one of its claims is still waiting to be worked."""
    running(conn, run_id)
    waiting = ids_in(conn, run_id, "waiting")
    if waiting:
        raise Refused(f"Still waiting: {', '.join(waiting)}")
    return close(conn, run_id, "finished", None)


def stop(conn: Connection, run_id: str, reason: str) -> Run:
    """Stop the run, leaving its claims as they are for the next dispatch."""
    running(conn, run_id)
    return close(conn, run_id, "stopped", reason)
