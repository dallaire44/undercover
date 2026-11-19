"""The agent's service: the one place the agent runs. The backend calls it.

Each operation answers at once and does its work in the background. When the
service starts, it carries on whatever the agent left when it last stopped.
"""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI

from agent import harness


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Set up the checkpointer, then carry on the agent's work in the background."""
    harness.set_up_checkpoints()
    threading.Thread(target=harness.pick_up, daemon=True).start()
    yield


app = FastAPI(title="UnderCover Agent", lifespan=lifespan)


@app.get("/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the agent's service is running."""
    return {"status": "ok"}


@app.post("/runs/{run_id}", operation_id="work_run", status_code=202)
def work_run(run_id: str, tasks: BackgroundTasks) -> dict[str, str]:
    """Carry on, then run the queue agent on the run."""
    tasks.add_task(harness.work_run, run_id)
    return {"run_id": run_id}


@app.post("/runs/{run_id}/claims/{claim_id}", operation_id="work_one", status_code=202)
def work_one(run_id: str, claim_id: str, tasks: BackgroundTasks) -> dict[str, str]:
    """Carry on, then work one claim and finish the run with its outcome."""
    tasks.add_task(harness.work_one, run_id, claim_id)
    return {"run_id": run_id, "claim_id": claim_id}


@app.post("/claims/{claim_id}/resume", operation_id="resume_claim", status_code=202)
def resume_claim(claim_id: str, tasks: BackgroundTasks) -> dict[str, str]:
    """Pick a signed-off claim back up and pay it."""
    tasks.add_task(harness.resume, claim_id)
    return {"claim_id": claim_id}
