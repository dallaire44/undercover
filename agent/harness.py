"""The harness: the model, its middleware, the queue agent and the claim agents."""

import json
import os
import uuid
from collections.abc import Callable, Iterator
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    wrap_tool_call,
)
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.types import Command
from pydantic import SecretStr

from agent import api, tools

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
TIMEOUT_SECONDS = 120
CLAIM_MODEL_CALLS = 30
CLAIM_RETRIES = 2
QUEUE_RETRIES = 5
RETRY_DELAY_SECONDS = 2.0
ERROR_CHARS = 300
VERDICTS = {"decline": "declined", "refer": "referred"}


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or DeepSeek V4.1 Flash by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


@wrap_tool_call
def refusals_as_text(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command[Any]:
    """Give a refused backend call back to the model as text, so it can put it right."""
    try:
        return handler(request)
    except api.Refused as refusal:
        call = request.tool_call
        return ToolMessage(str(refusal), tool_call_id=call["id"], name=call["name"])


def retries(times: int) -> ModelRetryMiddleware:
    """Retry a failed model call `times` times with backoff, then raise."""
    return ModelRetryMiddleware(
        max_retries=times, initial_delay=RETRY_DELAY_SECONDS, on_failure="error"
    )


def claim_middleware() -> list[AgentMiddleware[Any, Any]]:
    """Return refusals as text, retry failed model calls, stop a claim that loops."""
    return [
        refusals_as_text,
        retries(CLAIM_RETRIES),
        ModelCallLimitMiddleware(run_limit=CLAIM_MODEL_CALLS, exit_behavior="error"),
    ]


def queue_middleware() -> list[AgentMiddleware[Any, Any]]:
    """Return refusals as text, and retry more often, since a failure stops the run."""
    return [refusals_as_text, retries(QUEUE_RETRIES)]


def tracing(claim_id: str, thread_id: str) -> RunnableConfig:
    """Trace a claim in Langfuse, in one session per attempt, when the keys are set."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return {}
    return {
        "callbacks": [CallbackHandler()],
        "metadata": {"langfuse_session_id": f"{claim_id} {thread_id}"},
    }


def steps_of(message: BaseMessage) -> list[tuple[str, str]]:
    """Turn one message into the steps (kind, text) to show the handler."""
    if isinstance(message, ToolMessage):
        kind = "read" if message.name == "read_section" else "tool_result"
        return [(kind, str(message.text))]
    if not isinstance(message, AIMessage):
        return []
    text = str(message.text).strip()
    found: list[tuple[str, str]] = [("message", text)] if text else []
    for call in message.tool_calls:
        found.append(("tool_call", f"{call['name']}({json.dumps(call['args'])})"))
    return found


def run_claim(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run a claim agent on one claim, posting each step, and return its last reply."""
    agent = create_agent(
        llm or model(),
        tools=tools.CLAIM_TOOLS,
        system_prompt=api.get_instructions("claim"),
        middleware=claim_middleware(),
    )
    stream = agent.stream(
        {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
        tracing(claim_id, thread_id),
        stream_mode="updates",
        version="v2",
    )
    reply = ""
    for chunk in cast(Iterator[dict[str, Any]], stream):
        for update in chunk["data"].values():
            for message in (update or {}).get("messages", []):
                for kind, text in steps_of(message):
                    api.add_step(claim_id, thread_id, kind, text)
                    reply = text if kind == "message" else reply
    return reply


def outcome(record: api.Json) -> str:
    """Describe a finished claim in a few words."""
    decision = record["decision"]
    if record["status"] == "awaiting_sign_off":
        return f"approved, ${decision['payout']:,.2f} waiting for sign-off"
    if decision["decision"] == "approve":
        return f"approved, ${record['payment']['amount']:,.2f} paid"
    return VERDICTS[decision["decision"]]


def work_claim(run_id: str, claim_id: str) -> str:
    """Take a claim into the run, work it with a fresh claim agent, report one line."""
    try:
        api.take_claim(run_id, claim_id)
    except api.Refused as refusal:
        return f"{claim_id}: not taken. {refusal.detail}"
    thread_id = str(uuid.uuid4())
    api.add_step(claim_id, thread_id, "message", "Agent started")
    problem = "The agent finished without completing the claim."
    try:
        run_claim(claim_id, thread_id)
    except Exception as error:  # noqa: BLE001
        problem = f"The agent failed: {error}"[:ERROR_CHARS]
    record = api.get_claim(claim_id)
    if record["status"] != "in_progress":
        api.add_step(claim_id, thread_id, "message", "Agent finished")
        return f"{claim_id}: {outcome(record)}"
    if api.return_claim(claim_id, thread_id, problem)["status"] == "needs_handler":
        return f"{claim_id}: failed twice, left for a handler. {problem}"
    return f"{claim_id}: failed, back in the queue to try again. {problem}"


def run_queue(run_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the queue agent on a run, and return its last reply."""
    agent = create_agent(
        llm or model(),
        tools=tools.QUEUE_TOOLS,
        system_prompt=api.get_instructions("queue"),
        middleware=queue_middleware(),
        context_schema=tools.RunContext,
    )
    request = {"role": "user", "content": f"Work the queue for run {run_id}."}
    result = agent.invoke({"messages": [request]}, context=tools.RunContext(run_id))
    return result["messages"][-1].text
