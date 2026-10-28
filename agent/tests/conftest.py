import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pydantic import Field

from agent import main
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    seen: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(messages)
        return super()._generate(messages, *args, **kwargs)


def tool_call(name, **args):
    return {"name": name, "args": args, "id": f"{name}-{len(args)}"}


def stub(*replies: AIMessage) -> StubModel:
    return StubModel(messages=iter(replies))


@pytest.fixture
def api(tmp_path, monkeypatch):
    """The backend on a temporary database, as the agent's backend client."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "agent.db"))
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    return TestClient(app)
