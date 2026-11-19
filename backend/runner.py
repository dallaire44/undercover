"""Start the agent on a run in the background, and stop the run if the agent fails."""

import os

from fastapi import BackgroundTasks
from sqlalchemy import Connection

from agent import harness
from backend import db, records, runs
from backend.errors import Refused
from backend.models import Run


def agent_on() -> bool:
    """Say whether runs start the agent. The e2e backend sets UNDERCOVER_AGENT=off."""
    return os.getenv("UNDERCOVER_AGENT") != "off"


def start_run(conn: Connection, cap: int, tasks: BackgroundTasks) -> Run:
    """Start a run capped at `cap` claims, worked by the queue agent."""
    run = runs.start(conn, cap)
    if agent_on():
        tasks.add_task(run_queue, run.run_id)
    return run


def start_one(conn: Connection, claim_id: str, tasks: BackgroundTasks) -> Run:
    """Start a run on one waiting claim, worked by a claim agent alone."""
    if records.status(conn, claim_id) != "waiting":
        raise Refused(f"{claim_id} is not waiting")
    run = runs.start(conn, 1)
    if agent_on():
        tasks.add_task(run_one, run.run_id, claim_id)
    return run


def run_queue(run_id: str) -> None:
    """Run the queue agent. If it fails or never finishes, stop the run."""
    reason = "The agent ended without finishing the run."
    try:
        harness.run_queue(run_id)
    except Exception as error:  # noqa: BLE001
        reason = f"The agent failed: {error}"
    with db.connect() as conn:
        if runs.row(conn, run_id)["status"] == "running":
            runs.stop(conn, run_id, reason)


def run_one(run_id: str, claim_id: str) -> None:
    """Work one claim, then finish the run with its outcome."""
    outcome = harness.work_claim(run_id, claim_id)
    with db.connect() as conn:
        runs.close(conn, run_id, "finished", outcome)
