"""Response models for the API."""

from typing import Literal

from pydantic import BaseModel, Field

State = Literal["waiting", "in_progress", "awaiting_sign_off", "decided"]
Verdict = Literal["approve", "decline", "refer"]
StepKind = Literal["message", "tool_call", "tool_result"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Decision(BaseModel):
    decision: Verdict
    payout: float
    reason: str
    policy_section: str
    decided_at: str


class Payment(BaseModel):
    amount: float
    paid_at: str


class SignOff(BaseModel):
    handler_id: str
    handler_name: str
    signed_at: str


class ClaimCore(BaseModel):
    claim_id: str
    summary: str
    claim_type: str
    amount_claimed: float
    submitted_on: str
    customer_name: str
    status: State


class ClaimSummary(ClaimCore):
    decision: Verdict | None
    payout: float | None


class Claim(ClaimCore):
    policy_id: str
    customer_id: str
    incident_date: str
    incident_location: str
    story: str
    items: list[Item]
    documents: list[Document]
    decision: Decision | None
    payment: Payment | None
    sign_off: SignOff | None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
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


class ClaimHistory(BaseModel):
    customer_id: str
    name: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    email: str
    can_approve_over_limit: bool


class Text(BaseModel):
    text: str


class DecisionIn(BaseModel):
    decision: Verdict
    payout: float = Field(ge=0)
    reason: str
    policy_section: str


class PaymentIn(BaseModel):
    amount: float


class SignOffIn(BaseModel):
    handler_id: str


class StepIn(BaseModel):
    thread_id: str
    kind: StepKind
    text: str


class Step(StepIn):
    id: int
    created_at: str
