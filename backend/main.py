"""The UnderCover backend."""

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from backend import records
from backend.db import DATA, get_db
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Handler,
    Policy,
    Text,
)

app = FastAPI(title="UnderCover")

Db = Annotated[sqlite3.Connection, Depends(get_db)]
INSTRUCTIONS = Path(__file__).with_name("instructions.md")


def found[T](record: T | None, what: str) -> T:
    """Return the record, or answer 404."""
    if record is None:
        raise HTTPException(status_code=404, detail=f"{what} not found")
    return record


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(db: Db) -> list[ClaimSummary]:
    """List every claim in the queue with its status."""
    return records.list_claims(db)


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, db: Db) -> Claim:
    """Get one claim in full, with its decision, payment and sign-off."""
    return found(records.get_claim(db, claim_id), "Claim")


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, db: Db) -> Policy:
    """Get a policy with its plan, add-ons, trip and travelers."""
    return found(records.get_policy(db, policy_id), "Policy")


@app.get("/api/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(customer_id: str, db: Db) -> ClaimHistory:
    """Get a customer's name and earlier claims, without contact details."""
    return found(records.get_claim_history(db, customer_id), "Customer")


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording, the contract with the customer."""
    return Text(text=(DATA / "policy_wording.md").read_text())


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text())


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(db: Db) -> list[Handler]:
    """List the claims handlers."""
    return records.list_handlers(db)
