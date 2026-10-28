"""The UnderCover backend."""

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from backend import records, rules, steps
from backend.db import DATA, get_db
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    DecisionIn,
    Handler,
    PaymentIn,
    Policy,
    SignOffIn,
    Step,
    StepIn,
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


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, body: DecisionIn, db: Db) -> Claim:
    """Record the agent's decision on a claim: approve, decline or refer."""
    rules.record_decision(db, claim_id, body)
    return found(records.get_claim(db, claim_id), "Claim")


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, body: PaymentIn, db: Db) -> Claim:
    """Pay an approved claim for exactly the approved payout."""
    rules.pay_claim(db, claim_id, body.amount)
    return found(records.get_claim(db, claim_id), "Claim")


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, body: SignOffIn, db: Db) -> Claim:
    """Sign off a payout over the limit as a handler, which releases the payment."""
    rules.sign_off(db, claim_id, body.handler_id)
    return found(records.get_claim(db, claim_id), "Claim")


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, db: Db) -> list[Step]:
    """List the agent's steps on a claim, oldest first."""
    return steps.list_steps(db, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, body: StepIn, db: Db) -> Step:
    """Add one step the agent took on a claim."""
    return steps.add_step(db, claim_id, body)
