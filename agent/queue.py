"""The queue agent: works a run, handing each claim to a fresh claim agent."""

import uuid
from dataclasses import dataclass
from typing import Literal

import httpx
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from agent import api, claim
from agent.model import model, queue_middleware
from agent.tools import call

ERROR_CHARS = 300
VERDICTS = {"decline": "declined", "refer": "referred"}


@dataclass
class RunContext:
    run_id: str


class TodoItem(BaseModel):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


def note(client: httpx.Client, claim_id: str, thread_id: str, text: str) -> None:
    """Record a step written by the harness, not by the model."""
    body = {"thread_id": thread_id, "kind": "message", "text": text}
    client.post(f"/api/claims/{claim_id}/steps", json=body)


def outcome(record: dict) -> str:
    """Describe a finished claim in a few words."""
    decision = record["decision"]
    if record["status"] == "awaiting_sign_off":
        return f"approved, ${decision['payout']:,.2f} waiting for sign-off"
    if decision["decision"] == "approve":
        return f"approved, ${record['payment']['amount']:,.2f} paid"
    return VERDICTS[decision["decision"]]


def work_claim(run_id: str, claim_id: str) -> str:
    """Take a claim into the run, work it with a fresh claim agent, report one line."""
    with api.backend() as client:
        taken = client.post(f"/api/runs/{run_id}/claims/{claim_id}")
        if taken.is_client_error:
            return f"{claim_id}: not taken. {taken.json()['detail']}"
        thread_id = str(uuid.uuid4())
        note(client, claim_id, thread_id, "Agent started")
        problem = "The agent finished without completing the claim."
        try:
            claim.run(claim_id, thread_id)
        except Exception as error:  # noqa: BLE001
            problem = f"The agent failed: {error}"[:ERROR_CHARS]
        record = client.get(f"/api/claims/{claim_id}").json()
        if record["status"] != "in_progress":
            note(client, claim_id, thread_id, "Agent finished")
            return f"{claim_id}: {outcome(record)}"
        body = {"thread_id": thread_id, "reason": problem}
        returned = client.post(f"/api/claims/{claim_id}/return", json=body).json()
    if returned["status"] == "needs_handler":
        return f"{claim_id}: failed twice, left for a handler. {problem}"
    return f"{claim_id}: failed, back in the queue to try again. {problem}"


def line(found: dict) -> str:
    """Describe a claim to work in one line."""
    return (
        f"{found['claim_id']}: {found['claim_type'].replace('_', ' ')}, "
        f"${found['amount_claimed']:,.2f}, submitted {found['submitted_on']}, "
        f"{found['attempts']} earlier attempts. {found['summary']}"
    )


@tool("list_claims_to_work")
def list_claims_to_work_tool(runtime: ToolRuntime[RunContext]) -> str:
    """List the waiting claims this run may still work."""
    run_id = runtime.context.run_id
    with api.backend() as client:
        run = client.get(f"/api/runs/{run_id}").json()
        found = client.get(f"/api/runs/{run_id}/claims-to-work").json()
    if not found:
        return "No claims left to work."
    room = run["cap"] - len(run["claim_ids"])
    header = (
        f"The run's cap is {run['cap']} claims. It has taken {len(run['claim_ids'])}, "
        f"so it can take {room} more, plus any of its own back in the queue."
    )
    return "\n".join([header, *(line(c) for c in found)])


@tool("write_todos")
def write_todos_tool(todos: list[TodoItem], runtime: ToolRuntime[RunContext]) -> str:
    """Replace your to-do list. Send the whole list, in order, every time."""
    body = {"todos": [todo.model_dump() for todo in todos]}
    call("PUT", f"/api/runs/{runtime.context.run_id}/todos", body)
    return "To-do list saved."


@tool("work_claim")
def work_claim_tool(claim_id: str, runtime: ToolRuntime[RunContext]) -> str:
    """Work one claim with a fresh claim agent. Returns the outcome in one line."""
    return work_claim(runtime.context.run_id, claim_id)


@tool("finish_run")
def finish_run_tool(summary: str, runtime: ToolRuntime[RunContext]) -> str:
    """Finish the run with your summary for the handlers."""
    body = {"summary": summary}
    reply = call("POST", f"/api/runs/{runtime.context.run_id}/finish", body)
    return reply if reply.startswith("Refused") else "Run finished."


TOOLS = [list_claims_to_work_tool, write_todos_tool, work_claim_tool, finish_run_tool]


def run_queue(run_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the queue agent on a run, and return its last reply."""
    with api.backend() as client:
        instructions = client.get("/api/instructions/queue").text
    agent = create_agent(
        llm or model(),
        tools=TOOLS,
        system_prompt=instructions,
        middleware=queue_middleware(),
        context_schema=RunContext,
    )
    request = {"role": "user", "content": f"Work the queue for run {run_id}."}
    result = agent.invoke({"messages": [request]}, context=RunContext(run_id))
    return result["messages"][-1].text
