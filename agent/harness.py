"""The harness: the model, the claim agent's graph, and working a claim with it.

The claim agent is a LangGraph graph saved after every step, so it can wait for a
handler's sign-off and carry on after a restart. `work_claim` is the dispatcher's
one way in.
"""

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Annotated, Any, TypedDict, cast

from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.exceptions import ModelRateLimitError, ModelTimeoutError
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_openai import ChatOpenAI
from langfuse import propagate_attributes
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command, RetryPolicy, interrupt
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import SecretStr

from agent import api, tools

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
DEFAULT_EFFORT = "low"
TIMEOUT_SECONDS = 120
CLAIM_MODEL_CALLS = 30
CLAIM_RETRIES = 2
RETRY_DELAY_SECONDS = 2.0
ERROR_CHARS = 300
CHECKPOINT_CONNECTIONS = 4
POOL_WAIT_SECONDS = 120
SCHEMA = "undercover"
VERDICTS = {"decline": "declined", "refer": "referred"}
RETRIED = (ModelRateLimitError, ModelTimeoutError)


def model_settings() -> tuple[str, str]:
    """Return the model's name and reasoning effort: none for a model in MODEL_NAME."""
    name = os.getenv("MODEL_NAME")
    return (name, "none") if name else (DEFAULT_MODEL, DEFAULT_EFFORT)


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna on low effort by default."""
    name, effort = model_settings()
    return ChatOpenAI(
        model=name,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if effort == "none" else effort,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


@cache
def pool() -> ConnectionPool:
    """Return the process's pool of Supabase connections for checkpoints.

    Claim agents share its 4 connections and wait up to two minutes for one.
    """
    return ConnectionPool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=CHECKPOINT_CONNECTIONS,
        timeout=POOL_WAIT_SECONDS,
        open=False,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": f"-c search_path={SCHEMA}",
        },
    )


@cache
def memory() -> InMemorySaver:
    """Return the one in-memory checkpointer, used when DATABASE_URL is not set."""
    return InMemorySaver()


def saver() -> BaseCheckpointSaver:
    """Return a checkpointer for one claim run: its own, on the shared pool.

    A `PostgresSaver` holds a lock around every read and write, so claim agents
    sharing one would take turns.
    """
    if not os.getenv("DATABASE_URL"):
        return memory()
    return PostgresSaver(cast(Any, pool()))


def set_up_checkpoints() -> None:
    """Open the pool and create the checkpointer's tables, when on Supabase."""
    if os.getenv("DATABASE_URL"):
        pool().open(wait=True)
        PostgresSaver(cast(Any, pool())).setup()


@contextmanager
def tracing(
    claim_id: str, thread_id: str, run_id: str | None
) -> Iterator[RunnableConfig]:
    """Trace a claim in Langfuse, in one session per attempt, when the keys are set.

    The session and the run's tag are set on everything traced inside, since a
    claim worked inside the dispatcher's graph is not the root of its trace.
    """
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        yield {}
        return
    tags = [run_id] if run_id else None
    with propagate_attributes(session_id=f"{claim_id} {thread_id}", tags=tags):
        yield {"callbacks": [CallbackHandler()]}


def refused_as_text(
    request: ToolCallRequest,
    execute: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command[Any]:
    """Give a refused backend call back to the model as text, so it can put it right."""
    try:
        return execute(request)
    except api.Refused as refusal:
        call = request.tool_call
        return ToolMessage(str(refusal), tool_call_id=call["id"], name=call["name"])


class TooManyModelCalls(RuntimeError):
    """A claim agent went past its limit on model calls."""


class ClaimState(TypedDict):
    """What the graph keeps for one attempt on a claim."""

    messages: Annotated[list[AnyMessage], add_messages]
    claim_id: str
    model_calls: int
    decision: str | None
    status: str
    payout: float
    signed_off_by: str
    paid: float


@dataclass
class ClaimContext:
    """What every node of a claim graph shares: the model, its instructions, the run."""

    model: Runnable[LanguageModelInput, BaseMessage]
    instructions: SystemMessage
    run_id: str | None


type ClaimGraph = CompiledStateGraph[ClaimState, ClaimContext, ClaimState, ClaimState]


def agent(state: ClaimState, runtime: Runtime[ClaimContext]) -> dict[str, Any]:
    """Call the model with the conversation so far, up to the limit on model calls."""
    if state["model_calls"] >= CLAIM_MODEL_CALLS:
        raise TooManyModelCalls(f"Stopped after {CLAIM_MODEL_CALLS} model calls.")
    context = runtime.context
    reply = cast(
        AIMessage, context.model.invoke([context.instructions, *state["messages"]])
    )
    api.record_model_call(state["claim_id"], context.run_id, usage(reply))
    return {"messages": [reply], "model_calls": state["model_calls"] + 1}


def usage(reply: AIMessage) -> api.Json:
    """Return a reply's tokens and cost, as OpenRouter reports them."""
    tokens = reply.usage_metadata or {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": tokens["input_tokens"],
        "output_tokens": tokens["output_tokens"],
        "cost": reply.response_metadata["token_usage"]["cost"],
    }


def check(state: ClaimState) -> dict[str, Any]:
    """Read the claim back from the backend after a decision."""
    claim = api.get_claim(state["claim_id"])
    decision = claim["decision"] or {"decision": None, "payout": 0.0}
    return {
        "status": claim["status"],
        "decision": decision["decision"],
        "payout": decision["payout"],
    }


def sign_off(state: ClaimState) -> dict[str, Any]:
    """Wait for a handler to sign off a payout over the limit."""
    answer = interrupt({"claim_id": state["claim_id"], "payout": state["payout"]})
    return {"signed_off_by": answer["handler_name"]}


def pay(state: ClaimState) -> dict[str, Any]:
    """Pay the approved payout. A repeat after a restart counts as done."""
    api.pay_claim(state["claim_id"], state["payout"])
    return {"paid": state["payout"]}


def after_agent(state: ClaimState) -> str:
    """Run the tools the model asked for, or end when it asked for none."""
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and last.tool_calls else END


def after_tools(state: ClaimState) -> str:
    """Check the claim after a decision, or go back to the model."""
    calls = [m for m in state["messages"] if isinstance(m, AIMessage)][-1].tool_calls
    decided = any(c["name"] == "record_decision" for c in calls)
    return "check" if decided else "agent"


def after_check(state: ClaimState) -> str:
    """Wait for a sign-off, pay, or end, as the backend says."""
    if state["decision"] is None:
        return "agent"
    if state["status"] == "awaiting_sign_off":
        return "sign_off"
    return "pay" if state["decision"] == "approve" else END


def claim_graph() -> ClaimGraph:
    """Build the claim agent's graph, saved after every step."""
    retry = RetryPolicy(
        max_attempts=CLAIM_RETRIES + 1, initial_interval=RETRY_DELAY_SECONDS
    )
    builder = StateGraph(ClaimState, context_schema=ClaimContext)
    builder.add_node("agent", agent, retry_policy=retry)
    builder.add_node(
        "tools", ToolNode(tools.CLAIM_TOOLS, wrap_tool_call=refused_as_text)
    )
    builder.add_node("check", check)
    builder.add_node("sign_off", sign_off)
    builder.add_node("pay", pay)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", after_agent, ["tools", END])
    builder.add_conditional_edges("tools", after_tools, ["check", "agent"])
    builder.add_conditional_edges(
        "check", after_check, ["agent", "sign_off", "pay", END]
    )
    builder.add_edge("sign_off", "pay")
    builder.add_edge("pay", END)
    return builder.compile(checkpointer=saver())


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


def steps_of_update(node: str, update: Any) -> list[tuple[str, str]]:
    """Turn one node's update into the steps to show the handler."""
    if node == "__interrupt__":
        return [("message", "Waiting for a handler's sign-off.")]
    if node == "sign_off":
        return [("message", f"Signed off by {update['signed_off_by']}.")]
    if node == "pay":
        return [("message", f"Paid ${update['paid']:,.2f}.")]
    return [s for m in (update or {}).get("messages", []) for s in steps_of(m)]


def starting_point(
    graph: ClaimGraph, config: RunnableConfig, claim_id: str
) -> tuple[bool, Any]:
    """Say whether a claim's thread has work to do, and what to stream into it.

    A new thread starts with the claim, a thread waiting for a sign-off resumes with
    it once it is recorded, and a thread stopped partway carries on from its last step.
    """
    saved = graph.get_state(config)
    if saved.interrupts:
        signed = api.get_claim(claim_id)["sign_off"]
        return bool(signed), Command(resume=signed)
    if saved.next:
        return True, None
    if saved.values:
        return False, None
    first = HumanMessage(f"Decide claim {claim_id}.")
    return True, {"messages": [first], "claim_id": claim_id, "model_calls": 0}


def post_steps(claim_id: str, thread_id: str, stream: Iterator[Any]) -> None:
    """Post every step of a claim's graph on the claim, as it happens."""
    for chunk in stream:
        for node, update in chunk["data"].items():
            for kind, text in steps_of_update(node, update):
                api.add_step(claim_id, thread_id, kind, text)


@contextmanager
def timed(claim_id: str, run_id: str | None) -> Iterator[None]:
    """Record how long one stretch of work on a claim takes, even if it fails."""
    started = datetime.now(UTC)
    try:
        yield
    finally:
        seconds = (datetime.now(UTC) - started).total_seconds()
        when = started.isoformat(timespec="milliseconds")
        api.record_work_time(claim_id, run_id, when, seconds)


def run_claim(
    claim_id: str,
    thread_id: str,
    run_id: str | None,
    llm: BaseChatModel | None = None,
) -> None:
    """Start or carry on a claim's thread, posting each step, until it ends or waits.

    The time is recorded for each stretch of work, so a wait for a sign-off, when
    the graph is not running, is never counted.
    """
    graph = claim_graph()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    ready, start = starting_point(graph, config, claim_id)
    if not ready:
        return
    context = ClaimContext(
        model=(llm or model()).bind_tools(tools.CLAIM_TOOLS),
        instructions=SystemMessage(api.get_instructions("claim")),
        run_id=run_id,
    )
    with timed(claim_id, run_id), tracing(claim_id, thread_id, run_id) as traced:
        stream = graph.stream(
            start,
            {**config, **traced},
            context=context,
            stream_mode="updates",
            version="v2",
            durability="sync",
        )
        post_steps(claim_id, thread_id, stream)


def outcome(record: api.Json) -> str:
    """Describe a finished claim in a few words."""
    if record["status"] == "needs_handler":
        return "failed twice, left for a handler"
    decision = record["decision"]
    if record["status"] == "awaiting_sign_off":
        return f"approved, ${decision['payout']:,.2f} waiting for sign-off"
    if decision["decision"] == "approve":
        return f"approved, ${record['payment']['amount']:,.2f} paid"
    return VERDICTS[decision["decision"]]


def attempt(claim_id: str, thread_id: str, run_id: str | None) -> str:
    """Work or carry on a claim on its thread, and return it to the queue on failure.

    A rate limit or a timeout is raised with the claim still in progress, so a
    retry carries it on from its last step.
    """
    problem = "The agent finished without completing the claim."
    try:
        run_claim(claim_id, thread_id, run_id)
    except RETRIED:
        raise
    except Exception as error:  # noqa: BLE001
        problem = f"The agent failed: {error}"[:ERROR_CHARS]
    record = api.get_claim(claim_id)
    if record["status"] != "in_progress":
        api.add_step(claim_id, thread_id, "message", "Agent finished")
        return f"{claim_id}: {outcome(record)}"
    if api.return_claim(claim_id, thread_id, problem)["status"] == "needs_handler":
        return f"{claim_id}: failed twice, left for a handler. {problem}"
    return f"{claim_id}: failed, back in the queue to try again. {problem}"


def take(run_id: str, claim_id: str) -> str:
    """Take a claim into the run and return its thread, marking a new one started."""
    waiting = api.get_claim(claim_id)["status"] == "waiting"
    thread_id = api.take_claim(run_id, claim_id)["thread_id"]
    if waiting:
        api.add_step(claim_id, thread_id, "message", "Agent started")
    return thread_id


def take_and_attempt(run_id: str, claim_id: str) -> str:
    """Take a claim into the run and work it, or say why it was not taken."""
    try:
        thread_id = take(run_id, claim_id)
    except api.Refused as refusal:
        return f"{claim_id}: not taken. {refusal.detail}"
    return attempt(claim_id, thread_id, run_id)


def work_claim(run_id: str, claim_id: str) -> str:
    """Work a claim in a run, once more if it fails once, and report it in one line.

    A waiting claim starts on a new thread, and one in progress carries on from
    its last step as the same attempt. This is the dispatcher's only way in.
    """
    line = take_and_attempt(run_id, claim_id)
    if api.get_claim(claim_id)["status"] == "waiting":
        line = take_and_attempt(run_id, claim_id)
    return line


def resume(claim_id: str) -> None:
    """Pick a claim back up after its sign-off, and pay it."""
    attempt(claim_id, api.get_claim(claim_id)["thread_id"], None)
