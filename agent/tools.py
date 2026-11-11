"""The agents' tools: the claim agent's, then the queue agent's.

A refused backend call raises `api.Refused`, which the harness hands back to the model.
`work_claim` runs a claim agent, so this module and the harness import each other.
"""

import json
from dataclasses import dataclass
from typing import Literal

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel

from agent import api, harness


@dataclass
class RunContext:
    run_id: str


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


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim exactly the amount of its payout."""
    return json.dumps(api.pay_claim(claim_id, amount))


CLAIM_TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    list_sections,
    search_documents,
    read_section,
    record_decision,
    pay_claim,
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
