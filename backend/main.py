"""The UnderCover backend."""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import PlainTextResponse

from backend import db, records
from backend.models import (
    ClaimDetail,
    ClaimSummary,
    CustomerHistory,
    Handler,
    Policy,
)

HERE = Path(__file__).parent
Db = Depends(db.get_db)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create and seed the database on first start."""
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


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
    "/api/policy-wording",
    operation_id="get_policy_wording",
    response_class=PlainTextResponse,
)
def get_policy_wording() -> str:
    """Get the policy wording as Markdown."""
    return (db.DATA / "policy_wording.md").read_text(encoding="utf-8")


@app.get(
    "/api/instructions",
    operation_id="get_instructions",
    response_class=PlainTextResponse,
)
def get_instructions() -> str:
    """Get the agent's instructions as Markdown."""
    return (HERE / "instructions.md").read_text(encoding="utf-8")


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: sqlite3.Connection = Db) -> list[Handler]:
    """List the claims handlers."""
    return records.list_handlers(conn)
