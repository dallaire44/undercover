import random
import re
from collections.abc import Iterator
from contextlib import nullcontext
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agent import api, dispatcher, harness
from agent import service as agent_service_app
from backend import agent_service, db
from backend.main import app

REAL_POST = agent_service.post


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies, each with tokens and a cost."""

    cost: float = 0.01

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)
        reply = cast(AIMessage, result.generations[0].message)
        reply.usage_metadata = {
            "input_tokens": 1000,
            "output_tokens": 100,
            "total_tokens": 1100,
        }
        reply.response_metadata = {"token_usage": {"cost": self.cost}}
        return result


@pytest.fixture(autouse=True)
def fresh_checkpoints(monkeypatch):
    """A fresh in-memory checkpointer for each test, since run ids repeat."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    harness.memory.cache_clear()
    yield
    harness.memory.cache_clear()


@pytest.fixture(autouse=True)
def agent_calls(monkeypatch):
    """Record what the backend asks of the agent's service, without doing it."""
    calls: list[tuple[str, Any]] = []
    monkeypatch.setattr(agent_service, "post", lambda *call: calls.append(call))
    return calls


@pytest.fixture
def service(monkeypatch):
    """Send the backend's calls to the agent's service, run in this process."""
    monkeypatch.setattr(agent_service, "post", REAL_POST)
    monkeypatch.setattr(
        agent_service,
        "agent",
        lambda: nullcontext(TestClient(agent_service_app.app)),
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client on its own seeded database, which the agent's tools also use.

    The agent's client skips the app's startup, which runs once in a real backend.
    """
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    db.init()
    monkeypatch.setattr(api, "backend", lambda: nullcontext(TestClient(app)))
    return TestClient(app)


def call(name, **args):
    """A scripted model reply that calls one tool."""
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"id-{name}"}]
    )


def stub(*replies):
    """A stub model that gives the replies in order."""
    return StubModel(messages=iter(replies))


class Recorder(StubModel):
    """A stub model that also keeps the messages of every call it gets."""

    seen: list = []

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


class StopsOnce(Recorder):
    """A stub model stopped partway, as by Ctrl-C, on its call number `stop_at`."""

    stop_at: int = 3
    stopped: bool = False

    def _generate(self, messages, *args, **kwargs):
        if len(self.seen) == self.stop_at and not self.stopped:
            self.stopped = True
            raise KeyboardInterrupt
        return super()._generate(messages, *args, **kwargs)


def decide(client, claim_id, decision="decline", payout=0.0):
    """Record a decision on a claim, as a claim agent would."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": "The wording settles it.",
        "policy_section": "5. Baggage and Personal Effects",
    }
    client.post(f"/api/claims/{claim_id}/decision", json=body)


def dispatch_id(client, agents=3):
    """Create a dispatch, as the agent's service does, and return its id."""
    body = {"agents": agents, "model": "stub", "reasoning_effort": "none"}
    return client.post("/api/dispatches", json=body).json()["run_id"]


def all_but(client, *claim_ids):
    """The queue's claims other than these, for a dispatch to skip."""
    every = {c["claim_id"] for c in client.get("/api/claims").json()}
    return every - set(claim_ids)


class Script:
    """What the stub claim agents do: each claim's decision, and errors to raise.

    `errors` gives a claim's model calls in order: an error to raise, or None to
    reply as usual. `calls` keeps each call's claim id and messages.
    """

    def __init__(self) -> None:
        self.decisions: dict[str, tuple[str, float]] = {}
        self.errors: dict[str, list[BaseException | None]] = {}
        self.calls: list[tuple[str, list]] = []


class Decider(StubModel):
    """A stub claim agent: reads the claim and the contents, then decides it."""

    script: Script
    messages: Iterator = iter(())

    def reply(self, claim_id: str, messages: list) -> AIMessage:
        done = [m.name for m in messages if isinstance(m, ToolMessage)]
        if not done:
            return call("get_claim", claim_id=claim_id)
        if done[-1] == "get_claim":
            return call("list_sections")
        decision, payout = self.script.decisions.get(claim_id, ("decline", 0.0))
        return call(
            "record_decision",
            claim_id=claim_id,
            decision=decision,
            payout=payout,
            reason="The wording settles it.",
            policy_section="5. Baggage and Personal Effects",
        )

    def _generate(self, messages, *args, **kwargs):
        found = re.search(r"Decide claim (\S+)\.", messages[1].text)
        claim_id = cast(re.Match, found).group(1)
        self.script.calls.append((claim_id, list(messages)))
        planned = self.script.errors.get(claim_id)
        if planned and (error := planned.pop(0)):
            raise error
        self.messages = iter([self.reply(claim_id, messages)])
        return super()._generate(messages, *args, **kwargs)


@pytest.fixture
def script(monkeypatch):
    """Stub claim agents for every claim a dispatch works, with no waits to retry."""
    found = Script()
    monkeypatch.setattr(harness, "model", lambda: Decider(script=found))
    monkeypatch.setattr(harness, "RETRY_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(dispatcher, "FIRST_WAIT_SECONDS", 0.0)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)
    return found
