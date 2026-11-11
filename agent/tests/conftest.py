from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import api
from backend import db
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


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


def decide(client, claim_id, decision="decline", payout=0.0):
    """Record a decision on a claim, as a claim agent would."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": "The wording settles it.",
        "policy_section": "5. Baggage and Personal Effects",
    }
    client.post(f"/api/claims/{claim_id}/decision", json=body)
