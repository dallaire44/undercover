"""The UnderCover Agent."""

import json
import os
from collections.abc import Iterator
from typing import Any, cast

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent import api
from agent.tools import TOOLS

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


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
    """Turn one message into the steps (kind, text) to show the handler."""
    if isinstance(message, ToolMessage):
        return [("tool_result", str(message.text))]
    if not isinstance(message, AIMessage):
        return []
    found: list[tuple[str, str]] = (
        [("message", str(message.text))] if message.text else []
    )
    for call in message.tool_calls:
        found.append(("tool_call", f"{call['name']}({json.dumps(call['args'])})"))
    return found


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, posting each step, and return its last reply."""
    with api.backend() as client:
        instructions = client.get("/api/instructions").text
        agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
        stream = agent.stream(
            {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
            version="v2",
        )
        reply = ""
        for chunk in cast(Iterator[dict[str, Any]], stream):
            for update in chunk["data"].values():
                for message in update["messages"]:
                    for kind, text in steps_of(message):
                        body = {"thread_id": thread_id, "kind": kind, "text": text}
                        client.post(f"/api/claims/{claim_id}/steps", json=body)
                        reply = text if kind == "message" else reply
    return reply
