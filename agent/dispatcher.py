"""The dispatcher: works a run's claims with up to N claim agents at once.

A LangGraph graph with no model, as in the Week 2 Day 4 lab. Code chooses the
claims and keeps track of the run. Each claim saves its own progress on its own
thread, so the dispatcher saves none, and the next dispatch finishes what a
stopped one left.
"""

import operator
from collections.abc import Collection
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langchain_core.exceptions import ModelRateLimitError, ModelTimeoutError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy, Send

from agent import api, harness

ATTEMPTS = 3
FIRST_WAIT_SECONDS = 5.0
ERROR_CHARS = 300


class Dispatch(TypedDict):
    """What the dispatcher keeps for one run: its claims and a line for each."""

    run_id: str
    claim_ids: list[str]
    results: Annotated[list[str], operator.add]


class Task(TypedDict):
    """One claim for a claim agent to work."""

    run_id: str
    claim_id: str


@dataclass
class Orders:
    """Which claims to leave out (being resumed), or the one claim to work."""

    skip: Collection[str]
    only: str | None


type Dispatcher = CompiledStateGraph[Dispatch, Orders, Dispatch, Dispatch]


def list_claims(state: Dispatch, runtime: Runtime[Orders]) -> dict[str, Any]:
    """List the run's claims to work, leaving out any claim being resumed."""
    orders = runtime.context
    found = [c["claim_id"] for c in api.list_claims_to_work(state["run_id"])]
    if orders.only:
        found = [c for c in found if c == orders.only]
    return {"claim_ids": [c for c in found if c not in orders.skip]}


def fan_out(state: Dispatch) -> list[Send] | str:
    """Send each claim to a claim agent of its own, or finish if there are none."""
    sends = [
        Send("work_claim", Task(run_id=state["run_id"], claim_id=claim_id))
        for claim_id in state["claim_ids"]
    ]
    return sends or "finish"


def work_claim(state: Task) -> dict[str, Any]:
    """Work one claim with the claim agent, and report it in one line."""
    return {"results": [harness.work_claim(state["run_id"], state["claim_id"])]}


def left_in_progress(state: Task) -> dict[str, Any]:
    """After the retries, leave the claim in progress for the next dispatch."""
    return {
        "results": [f"{state['claim_id']}: still in progress, for the next dispatch"]
    }


def finish(state: Dispatch) -> dict[str, Any]:
    """Finish the run once every claim has come back."""
    api.finish_run(state["run_id"])
    return {}


def dispatcher() -> Dispatcher:
    """Build the dispatcher's graph, which saves no progress of its own."""
    retry = RetryPolicy(
        max_attempts=ATTEMPTS,
        initial_interval=FIRST_WAIT_SECONDS,
        retry_on=(ModelRateLimitError, ModelTimeoutError),
    )
    builder = StateGraph(Dispatch, context_schema=Orders)
    builder.add_node("list_claims", list_claims)
    builder.add_node(
        "work_claim", work_claim, retry_policy=retry, error_handler=left_in_progress
    )
    builder.add_node("finish", finish)
    builder.add_edge(START, "list_claims")
    builder.add_conditional_edges("list_claims", fan_out, ["work_claim", "finish"])
    builder.add_edge("work_claim", "finish")
    builder.add_edge("finish", END)
    return builder.compile()


def dispatch(
    run_id: str, agents: int, skip: Collection[str], only: str | None
) -> list[str]:
    """Work the run's claims, up to `agents` at once, finish it, and return the lines.

    If the dispatch fails, the run is stopped with the reason.
    """
    start = Dispatch(run_id=run_id, claim_ids=[], results=[])
    try:
        result = dispatcher().invoke(
            start, {"max_concurrency": agents}, context=Orders(skip, only)
        )
    except Exception as error:
        api.stop_run(run_id, f"The dispatcher failed: {error}"[:ERROR_CHARS])
        raise
    return result["results"]
