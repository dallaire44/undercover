"""The agents' tools: the claim agent's, then the queue agent's.

A refused backend call raises `api.Refused`, which the harness hands back to the model.
`work_claim` runs a claim agent, so this module and the harness import each other.
"""

import json
from dataclasses import dataclass
from typing import Literal

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from agent import api, harness


@dataclass
class RunContext:
    run_id: str


class Line(BaseModel):
    """One covered item or expense on a claim."""

    description: str = Field(description="What the item or expense is")
    amount: float = Field(
        description="The total claimed for the line in US dollars, before any "
        "limits. For several items, the total for all of them"
    )
    quantity: int = Field(
        ge=1,
        description="How many separate items the line holds, such as 3 for three "
        "shirts. A pair or a set is one item",
    )
    kind: Literal[
        "item", "electronics", "cash", "expense", "hotel", "meals_without_receipts"
    ] = Field(
        description=(
            "item: a belonging, or a pair or set that counts as one item. "
            "electronics: only a phone, tablet, laptop, camera or its lens, e-reader "
            "or smartwatch; any other device is an item. "
            "cash: cash that was lost or stolen. "
            "expense: any other cost with a receipt, such as a medical bill, a meal, "
            "a taxi, a fee or a prepaid trip cost. "
            "hotel: a hotel during a trip delay. "
            "meals_without_receipts: meals during a trip delay with no receipts."
        )
    )
    nights: int = Field(ge=0, description="For a hotel, the number of nights, else 0")
    hours: float = Field(
        ge=0, description="For meals without receipts, the delay in hours, else 0"
    )


class TodoItem(BaseModel):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


@tool
def get_claim(claim_id: str) -> str:
    """Get one claim in full: its story, items and documents."""
    return json.dumps(api.get_claim(claim_id))


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy with its plan, trip and travelers."""
    return json.dumps(api.get_policy(policy_id))


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's name and earlier claims."""
    return json.dumps(api.get_claim_history(customer_id))


@tool
def list_sections() -> str:
    """List the sections of the policy wording and the claims manual."""
    return api.list_sections()


@tool
def search_documents(query: str) -> str:
    """Find the sections of the wording and the manual that match a few words."""
    return api.search_documents(query)


@tool
def read_section(
    document: Literal["policy_wording", "claims_manual"], number: str
) -> str:
    """Read one section of the policy wording or the claims manual, such as 9."""
    return api.read_section(document, number)


@tool(parse_docstring=True)
def calculate_payout(
    policy_id: str,
    benefit: Literal[
        "trip_cancellation",
        "trip_interruption",
        "trip_delay",
        "baggage_delay",
        "baggage",
        "passport",
        "emergency_medical",
    ],
    lines: list[Line],
    paid_by_others: float,
) -> str:
    """Work out the payout on an approved claim with UnderCover's payout rules.

    Args:
        policy_id: The customer's policy id
        benefit: The benefit the claim is paid under
        lines: The covered items and expenses, one for each line of the claim, with
            any excluded ones left out. A pair or a set counts as one item
        paid_by_others: Anything a carrier, hotel or other party has paid or
            refunded for the same loss, or 0
    """
    request = {
        "benefit": benefit,
        "lines": [line.model_dump() for line in lines],
        "paid_by_others": paid_by_others,
    }
    return api.calculate_payout(policy_id, request)


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim. The payout is 0 unless you approve."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return json.dumps(api.record_decision(claim_id, body))


CLAIM_TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    list_sections,
    search_documents,
    read_section,
    calculate_payout,
    record_decision,
]


def line(found: api.Json) -> str:
    """Describe a claim to work in one line."""
    return (
        f"{found['claim_id']}: {found['claim_type'].replace('_', ' ')}, "
        f"${found['amount_claimed']:,.2f}, submitted {found['submitted_on']}, "
        f"{found['attempts']} earlier attempts. {found['summary']}"
    )


@tool
def list_claims_to_work(runtime: ToolRuntime[RunContext]) -> str:
    """List the waiting claims this run may still work."""
    run_id = runtime.context.run_id
    found = api.list_claims_to_work(run_id)
    if not found:
        return "No claims left to work."
    run = api.get_run(run_id)
    room = run["cap"] - len(run["claim_ids"])
    header = (
        f"The run's cap is {run['cap']} claims. It has taken {len(run['claim_ids'])}, "
        f"so it can take {room} more, plus any of its own back in the queue."
    )
    return "\n".join([header, *(line(c) for c in found)])


@tool
def write_todos(todos: list[TodoItem], runtime: ToolRuntime[RunContext]) -> str:
    """Replace your to-do list. Send the whole list, in order, every time."""
    api.write_todos(runtime.context.run_id, [todo.model_dump() for todo in todos])
    return "To-do list saved."


@tool
def work_claim(claim_id: str, runtime: ToolRuntime[RunContext]) -> str:
    """Work one claim with a fresh claim agent. Returns the outcome in one line."""
    return harness.work_claim(runtime.context.run_id, claim_id)


@tool
def finish_run(summary: str, runtime: ToolRuntime[RunContext]) -> str:
    """Finish the run with your summary for the handlers."""
    api.finish_run(runtime.context.run_id, summary)
    return "Run finished."


QUEUE_TOOLS = [list_claims_to_work, write_todos, work_claim, finish_run]
