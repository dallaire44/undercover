"""The UnderCover backend."""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from backend import db, documents, records, rules, runner, runs, steps
from backend.errors import NotFound, Refused
from backend.models import (
    ClaimDetail,
    ClaimSummary,
    CustomerHistory,
    DecisionRecord,
    DecisionRequest,
    FinishRequest,
    Handler,
    Payment,
    PaymentRequest,
    Policy,
    ReturnRequest,
    Run,
    RunRequest,
    SignOff,
    SignOffRequest,
    Step,
    StepRequest,
    Todo,
    TodoList,
)

HERE = Path(__file__).parent
Db = Depends(db.get_db)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create and seed the database on first start, and stop any run left running."""
    db.init()
    with closing(db.connect()) as conn:
        runs.recover(conn)
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


@app.exception_handler(NotFound)
def not_found(_: Request, error: Exception) -> JSONResponse:
    """Answer 404 for a record that does not exist."""
    return JSONResponse({"detail": str(error)}, status_code=404)


@app.exception_handler(Refused)
def refused(_: Request, error: Exception) -> JSONResponse:
    """Answer 409 for a request the rules refuse."""
    return JSONResponse({"detail": str(error)}, status_code=409)


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: sqlite3.Connection = Db) -> list[ClaimSummary]:
    """List every claim in the queue."""
    return records.list_claims(conn)


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: sqlite3.Connection = Db) -> ClaimDetail:
    """Get one claim in full."""
    return records.get_claim(conn, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: sqlite3.Connection = Db) -> Policy:
    """Get a policy with its plan, trip and travelers."""
    return records.get_policy(conn, policy_id)


@app.get("/api/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(
    customer_id: str, conn: sqlite3.Connection = Db
) -> CustomerHistory:
    """Get a customer's name and earlier claims."""
    return records.get_history(conn, customer_id)


@app.get(
    "/api/documents", operation_id="list_sections", response_class=PlainTextResponse
)
def list_sections() -> str:
    """List the sections of the policy wording and the claims manual."""
    return documents.contents()


@app.get(
    "/api/documents/search",
    operation_id="search_documents",
    response_class=PlainTextResponse,
)
def search_documents(query: str) -> str:
    """Find the sections of the wording and the manual that match the query."""
    return documents.search(query)


@app.get(
    "/api/documents/{document}/sections/{number}",
    operation_id="read_section",
    response_class=PlainTextResponse,
)
def read_section(document: str, number: str) -> str:
    """Read one section of the policy wording or the claims manual."""
    return documents.read(document, number)


@app.get(
    "/api/instructions/{agent}",
    operation_id="get_instructions",
    response_class=PlainTextResponse,
)
def get_instructions(agent: Literal["queue", "claim"]) -> str:
    """Get an agent's instructions as Markdown."""
    return (HERE / "instructions" / f"{agent}.md").read_text(encoding="utf-8")


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: sqlite3.Connection = Db) -> list[Handler]:
    """List the claims handlers."""
    return records.list_handlers(conn)


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, conn: sqlite3.Connection = Db) -> list[Step]:
    """List the agent's steps on a claim, oldest first."""
    return steps.list_steps(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(
    claim_id: str, request: StepRequest, conn: sqlite3.Connection = Db
) -> Step:
    """Add one step of the agent's work to a claim."""
    return steps.add_step(conn, claim_id, request)


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(
    claim_id: str, request: DecisionRequest, conn: sqlite3.Connection = Db
) -> DecisionRecord:
    """Record the decision on a claim: approve, decline or refer."""
    return rules.record_decision(conn, claim_id, request)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(
    claim_id: str, request: PaymentRequest, conn: sqlite3.Connection = Db
) -> Payment:
    """Pay an approved claim the amount of its payout."""
    return rules.pay_claim(conn, claim_id, request)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(
    claim_id: str, request: SignOffRequest, conn: sqlite3.Connection = Db
) -> SignOff:
    """Sign off a payout over the limit, which pays the claim."""
    return rules.sign_off(conn, claim_id, request)


@app.get("/api/runs/latest", operation_id="get_latest_run")
def get_latest_run(conn: sqlite3.Connection = Db) -> Run | None:
    """Get the latest run with its to-do list, or null before the first."""
    return runs.latest(conn)


@app.get("/api/runs/{run_id}", operation_id="get_run")
def get_run(run_id: str, conn: sqlite3.Connection = Db) -> Run:
    """Get one run with its claims, to-do list and summary."""
    return runs.get(conn, run_id)


@app.get("/api/runs/{run_id}/claims-to-work", operation_id="list_claims_to_work")
def list_claims_to_work(
    run_id: str, conn: sqlite3.Connection = Db
) -> list[ClaimSummary]:
    """List the waiting claims this run may still work."""
    return runs.claims_to_work(conn, run_id)


@app.post("/api/runs/{run_id}/claims/{claim_id}", operation_id="take_claim")
def take_claim(
    run_id: str, claim_id: str, conn: sqlite3.Connection = Db
) -> ClaimSummary:
    """Take a waiting claim into the run and start it, within the run's cap."""
    return runs.take_claim(conn, run_id, claim_id)


@app.post("/api/claims/{claim_id}/return", operation_id="return_claim")
def return_claim(
    claim_id: str, request: ReturnRequest, conn: sqlite3.Connection = Db
) -> ClaimSummary:
    """Return a claim after a failed attempt: to the queue, or to a handler."""
    return runs.return_claim(conn, claim_id, request)


@app.put("/api/runs/{run_id}/todos", operation_id="write_todos")
def write_todos(
    run_id: str, request: TodoList, conn: sqlite3.Connection = Db
) -> list[Todo]:
    """Replace the run's to-do list."""
    return runs.write_todos(conn, run_id, request.todos)


@app.post("/api/runs/{run_id}/finish", operation_id="finish_run")
def finish_run(
    run_id: str, request: FinishRequest, conn: sqlite3.Connection = Db
) -> Run:
    """Finish the run with a summary, once no claim is left to work."""
    return runs.finish(conn, run_id, request.summary)


@app.post("/api/runs", operation_id="start_run", status_code=202)
def start_run(
    request: RunRequest, tasks: BackgroundTasks, conn: sqlite3.Connection = Db
) -> Run:
    """Start a run of the agent on the queue, capped at a number of claims."""
    return runner.start_run(conn, request.cap, tasks)


@app.post("/api/claims/{claim_id}/agent", operation_id="start_agent", status_code=202)
def start_agent(
    claim_id: str, tasks: BackgroundTasks, conn: sqlite3.Connection = Db
) -> Run:
    """Start a run of the agent on one waiting claim."""
    return runner.start_one(conn, claim_id, tasks)
