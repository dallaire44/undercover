"""Start runs, and hand them to the agent's service to work."""

from fastapi import BackgroundTasks
from sqlalchemy import Connection

from backend import agent_service, db, records, runs
from backend.errors import Refused
from backend.models import Run

UNREACHED = "The agent's service could not be reached."


def start_run(conn: Connection, cap: int, tasks: BackgroundTasks) -> Run:
    """Start a run capped at `cap` claims, worked by the queue agent."""
    run = runs.start(conn, cap)
    tasks.add_task(work_run, run.run_id)
    return run


def start_one(conn: Connection, claim_id: str, tasks: BackgroundTasks) -> Run:
    """Start a run on one waiting claim, worked by a claim agent alone."""
    if records.status(conn, claim_id) != "waiting":
        raise Refused(f"{claim_id} is not waiting")
    run = runs.start(conn, 1)
    tasks.add_task(work_one, run.run_id, claim_id)
    return run


def work_run(run_id: str) -> None:
    """Ask the agent to work the run, or stop the run if it can't be reached."""
    if not agent_service.work_run(run_id):
        stop_unreached(run_id)


def work_one(run_id: str, claim_id: str) -> None:
    """Ask the agent to work one claim, or stop the run if it can't be reached."""
    if not agent_service.work_one(run_id, claim_id):
        stop_unreached(run_id)


def stop_unreached(run_id: str) -> None:
    """Stop a run the agent's service never took."""
    with db.connect() as conn:
        runs.stop(conn, run_id, UNREACHED)
