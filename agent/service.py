"""The agent's service: the one place the agent runs. The backend calls it.

It starts dispatches and evaluations, one run at a time, and resumes claims
after a sign-off. Each operation answers at once and works in the background.
When the service starts, it stops the run it left running; the next dispatch
carries its claims on.
"""

import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import partial
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent import api, dispatcher, harness

RUN_LOCK = threading.Lock()
RESUMING: set[str] = set()
BUSY = "A dispatch or evaluation is already running"
RESTARTED = "The agent's service restarted"


class DispatchStart(BaseModel):
    agents: int = Field(ge=1, le=25, description="How many claim agents work at once")


class EvaluationStart(DispatchStart):
    claim_set: Literal["evaluation", "held_out"]
    tiny: bool = Field(description="Only the set's five tiny claims")


def stop_left_running() -> None:
    """Stop the run the service was working when it last stopped, if any."""
    with RUN_LOCK:
        api.wait_for_backend()
        run = api.get_latest_run()
        if run and run["status"] == "running":
            api.stop_run(run["run_id"], RESTARTED)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Set up the checkpointer, then stop the run left running, in the background."""
    harness.set_up_checkpoints()
    threading.Thread(target=stop_left_running, daemon=True).start()
    yield


app = FastAPI(title="UnderCover Agent", lifespan=lifespan)


def work(create: Callable[[str, str], api.Json], agents: int, only: str | None) -> None:
    """Create the run through the backend, dispatch its claims, and free the lock."""
    try:
        run_id = create(*harness.model_settings())["run_id"]
        dispatcher.dispatch(run_id, agents, RESUMING, only)
    finally:
        RUN_LOCK.release()


def start(
    tasks: BackgroundTasks,
    create: Callable[[str, str], api.Json],
    agents: int,
    only: str | None,
) -> None:
    """Take the run lock and work the run in the background, or refuse."""
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=BUSY)
    tasks.add_task(work, create, agents, only)


def resume(claim_id: str) -> None:
    """Resume a claim after its sign-off, then let dispatches take it again."""
    try:
        harness.resume(claim_id)
    finally:
        RESUMING.discard(claim_id)


@app.get("/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the agent's service is running."""
    return {"status": "ok"}


@app.post("/dispatches", operation_id="start_dispatch", status_code=202)
def start_dispatch(request: DispatchStart, tasks: BackgroundTasks) -> None:
    """Dispatch the queue with N claim agents at once, unless a run is going."""
    start(tasks, partial(api.create_dispatch, request.agents), request.agents, None)


@app.post("/evaluations", operation_id="start_evaluation", status_code=202)
def start_evaluation(request: EvaluationStart, tasks: BackgroundTasks) -> None:
    """Evaluate a labelled set with N claim agents at once, unless a run is going."""
    create = partial(
        api.create_evaluation, request.agents, request.claim_set, request.tiny
    )
    start(tasks, create, request.agents, None)


@app.post("/claims/{claim_id}/work", operation_id="work_one", status_code=202)
def work_one(claim_id: str, tasks: BackgroundTasks) -> None:
    """Work one claim in a dispatch of its own, unless a run is going."""
    start(tasks, partial(api.create_dispatch, 1), 1, claim_id)


@app.post("/claims/{claim_id}/resume", operation_id="resume_claim", status_code=202)
def resume_claim(claim_id: str, tasks: BackgroundTasks) -> None:
    """Pick a signed-off claim back up and pay it, out of any dispatch."""
    RESUMING.add(claim_id)
    tasks.add_task(resume, claim_id)
