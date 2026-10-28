"""The UnderCover Agent."""

import json
import os
from collections.abc import Iterator
from typing import cast

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.types import UpdatesStreamPart
from pydantic import SecretStr

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return httpx.Client(base_url=url, timeout=30)


def call(method: str, path: str, body: dict | None = None) -> str:
    """Call the backend. A refusal (4xx) comes back as text, so the model sees why."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_client_error:
        return f"Refused ({response.status_code}): {response.json()['detail']}"
    response.raise_for_status()
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim in full: the story, the items claimed and the documents."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan, add-ons, trip dates and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's earlier claims."""
    return call("GET", f"/api/customers/{customer_id}/history")


@tool
def get_policy_wording() -> str:
    """Get the policy wording, the contract with the customer."""
    return call("GET", "/api/policy-wording")


@tool
def record_decision(
    claim_id: str, decision: str, payout: float, reason: str, policy_section: str
) -> str:
    """Record the decision: approve, decline or refer, with its payout and reason."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return call("POST", f"/api/claims/{claim_id}/decision", body)


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim, for exactly the approved payout."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    get_policy_wording,
    record_decision,
    pay_claim,
]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps_of(message: BaseMessage) -> list[tuple[str, str]]:
    """Turn one message into steps: (kind, text) pairs."""
    if isinstance(message, ToolMessage):
        return [("tool_result", str(message.text))]
    if not isinstance(message, AIMessage):
        return []
    steps = [("message", str(message.text))] if message.text else []
    for call_ in message.tool_calls:
        steps.append(("tool_call", f"{call_['name']}({json.dumps(call_['args'])})"))
    return steps


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> None:
    """Report one step to the backend."""
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    call("POST", f"/api/claims/{claim_id}/steps", body)


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, report each step, and return its final reply."""
    instructions = json.loads(call("GET", "/api/instructions"))["text"]
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    reply = ""
    stream = agent.stream(
        {"messages": [{"role": "user", "content": f"Claim {claim_id}"}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
        version="v2",
    )
    for chunk in cast(Iterator[UpdatesStreamPart], stream):
        for update in chunk["data"].values():
            for message in update["messages"]:
                for kind, text in steps_of(message):
                    add_step(claim_id, thread_id, kind, text)
                    reply = text if kind == "message" else reply
    return reply
