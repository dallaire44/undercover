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
    """A client on its own seeded database, which the agent's tools also use."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    db.init()
    monkeypatch.setattr(api, "backend", lambda: TestClient(app))
    return TestClient(app)


def call(name, **args):
    """A scripted model reply that calls one tool."""
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"id-{name}"}]
    )


def stub(*replies):
    """A stub model that gives the replies in order."""
    return StubModel(messages=iter(replies))
