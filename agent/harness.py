"""The harness: the model, the claim agent's graph, the queue agent, and running them.

The claim agent is a LangGraph graph saved after every step, so it can wait for a
handler's sign-off and carry on after a restart. The queue agent is `create_agent`
with the same checkpointer.
"""

import json
import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import Annotated, Any, TypedDict, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    wrap_tool_call,
)
from langchain.agents.middleware.types import ToolCallRequest
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
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
TIMEOUT_SECONDS = 120
CLAIM_MODEL_CALLS = 30
CLAIM_RETRIES = 2
QUEUE_RETRIES = 5
RETRY_DELAY_SECONDS = 2.0
ERROR_CHARS = 300
CHECKPOINT_CONNECTIONS = 4
SCHEMA = "undercover"
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


@cache
def checkpointer() -> BaseCheckpointSaver:
    """Save every step to Supabase when DATABASE_URL is set, or in memory otherwise."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return InMemorySaver()
    pool = ConnectionPool(
        url,
        min_size=1,
        max_size=CHECKPOINT_CONNECTIONS,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": f"-c search_path={SCHEMA}",
        },
    )
    return PostgresSaver(cast(Any, pool))


def set_up_checkpoints() -> None:
    """Create the checkpointer's tables in Supabase, if they are not there yet."""
    saver = checkpointer()
    if isinstance(saver, PostgresSaver):
        saver.setup()


@contextmanager
def tracing(claim_id: str, thread_id: str) -> Iterator[RunnableConfig]:
    """Trace a claim in Langfuse, in one session per attempt, when the keys are set.

    The session is set on everything traced inside, so a claim worked inside the
    queue agent's run lands in its own session too.
    """
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        yield {}
        return
    with propagate_attributes(session_id=f"{claim_id} {thread_id}"):
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
    """What every node of a claim graph shares: the model and its instructions."""

    model: Runnable[LanguageModelInput, BaseMessage]
    instructions: SystemMessage


type ClaimGraph = CompiledStateGraph[ClaimState, ClaimContext, ClaimState, ClaimState]


def agent(state: ClaimState, runtime: Runtime[ClaimContext]) -> dict[str, Any]:
    """Call the model with the conversation so far, up to the limit on model calls."""
    if state["model_calls"] >= CLAIM_MODEL_CALLS:
        raise TooManyModelCalls(f"Stopped after {CLAIM_MODEL_CALLS} model calls.")
    context = runtime.context
    reply = context.model.invoke([context.instructions, *state["messages"]])
    return {"messages": [reply], "model_calls": state["model_calls"] + 1}


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
    return builder.compile(checkpointer=checkpointer())


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


def run_claim(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> None:
    """Start or carry on a claim's thread, posting each step, until it ends or waits."""
    graph = claim_graph()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    ready, start = starting_point(graph, config, claim_id)
    if not ready:
        return
    context = ClaimContext(
        model=(llm or model()).bind_tools(tools.CLAIM_TOOLS),
        instructions=SystemMessage(api.get_instructions("claim")),
    )
    with tracing(claim_id, thread_id) as traced:
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


def attempt(claim_id: str, thread_id: str) -> str:
    """Work or carry on a claim on its thread, and return it to the queue on failure."""
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


def work_claim(run_id: str, claim_id: str) -> str:
    """Take a claim into the run, or carry on one it holds, and report one line."""
    record = api.get_claim(claim_id)
    if record["run_id"] == run_id and record["status"] != "waiting":
        if record["status"] == "in_progress":
            return attempt(claim_id, record["thread_id"])
        return f"{claim_id}: {outcome(record)}"
    try:
        thread_id = api.take_claim(run_id, claim_id)["thread_id"]
    except api.Refused as refusal:
        return f"{claim_id}: not taken. {refusal.detail}"
    api.add_step(claim_id, thread_id, "message", "Agent started")
    return attempt(claim_id, thread_id)


CARRYING_ON = threading.Lock()


def carry_on() -> None:
    """Carry on each claim left in progress: stopped partway, or signed off."""
    with CARRYING_ON:
        for claim in api.list_claims():
            if claim["status"] == "in_progress" and claim["thread_id"]:
                attempt(claim["claim_id"], claim["thread_id"])


def queue_middleware() -> list[AgentMiddleware[Any, Any]]:
    """Return refusals as text, and retry more often, since a failure stops the run."""
    return [
        wrap_tool_call(refused_as_text),
        ModelRetryMiddleware(
            max_retries=QUEUE_RETRIES,
            initial_delay=RETRY_DELAY_SECONDS,
            on_failure="error",
        ),
    ]


def run_queue(run_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the queue agent on a run, or carry on a run that was stopped."""
    agent_ = create_agent(
        llm or model(),
        tools=tools.QUEUE_TOOLS,
        system_prompt=api.get_instructions("queue"),
        middleware=queue_middleware(),
        context_schema=tools.RunContext,
        checkpointer=checkpointer(),
    )
    config: RunnableConfig = {"configurable": {"thread_id": run_id}}
    request = {"role": "user", "content": f"Work the queue for run {run_id}."}
    start = None if agent_.get_state(config).next else {"messages": [request]}
    result = agent_.invoke(
        cast(Any, start), config, context=tools.RunContext(run_id), durability="sync"
    )
    return result["messages"][-1].text


def work_run(run_id: str) -> None:
    """Carry on, then run the queue agent, and stop the run if it never finishes."""
    carry_on()
    reason = "The agent ended without finishing the run."
    try:
        run_queue(run_id)
    except Exception as error:  # noqa: BLE001
        reason = f"The agent failed: {error}"[:ERROR_CHARS]
    if api.get_run(run_id)["status"] == "running":
        api.stop_run(run_id, reason)


def work_one(run_id: str, claim_id: str) -> None:
    """Carry on, then work one claim (again if it fails once), and finish the run."""
    carry_on()
    line = work_claim(run_id, claim_id)
    if api.get_claim(claim_id)["status"] == "waiting":
        line = work_claim(run_id, claim_id)
    api.finish_run(run_id, line)


def resume(claim_id: str) -> None:
    """Pick a claim back up after its sign-off, and pay it."""
    attempt(claim_id, api.get_claim(claim_id)["thread_id"])


def has_queue_thread(run_id: str) -> bool:
    """Say whether a queue agent has worked the run, so has a thread to carry on."""
    return checkpointer().get_tuple({"configurable": {"thread_id": run_id}}) is not None


def pick_up() -> None:
    """When the agent starts, carry on the run left running, or claims in progress.

    A run on one claim has no queue agent, so it is finished with its claim's line.
    """
    api.wait_for_backend()
    run = api.get_latest_run()
    if not run or run["status"] != "running":
        carry_on()
    elif run["claim_ids"] and not has_queue_thread(run["run_id"]):
        work_one(run["run_id"], run["claim_ids"][0])
    else:
        work_run(run["run_id"])
