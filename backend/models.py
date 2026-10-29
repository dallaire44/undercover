"""The shapes the API returns and accepts."""

from typing import Literal

from pydantic import BaseModel

State = Literal["waiting", "in_progress", "awaiting_sign_off", "decided"]
Verdict = Literal["approve", "decline", "refer"]


class ClaimSummary(BaseModel):
    claim_id: str
    summary: str
    claim_type: str
    amount_claimed: float
    submitted_on: str
    customer_name: str
    status: State


class ClaimItem(BaseModel):
    description: str
    category: str
    amount: float


class ClaimDocument(BaseModel):
    name: str
    type: str
    content: str


class ClaimDetail(ClaimSummary):
    policy_id: str
    customer_id: str
    incident_date: str
    incident_location: str
    story: str
    items: list[ClaimItem]
    documents: list[ClaimDocument]
    decision: None = None
    payment: None = None
    sign_off: None = None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    plan_name: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class CustomerHistory(BaseModel):
    customer_id: str
    name: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    email: str
    can_approve_over_limit: bool
