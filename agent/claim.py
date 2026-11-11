"""The claim agent: works one claim from a fresh start."""

import json
from collections.abc import Iterator
from typing import Any, cast

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from agent import api
from agent.model import claim_middleware, model
from agent.tools import TOOLS


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


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, posting each step, and return its last reply."""
    with api.backend() as client:
        instructions = client.get("/api/instructions/claim").text
        agent = create_agent(
            llm or model(),
            tools=TOOLS,
            system_prompt=instructions,
            middleware=claim_middleware(),
        )
        stream = agent.stream(
            {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
            version="v2",
        )
        reply = ""
        for chunk in cast(Iterator[dict[str, Any]], stream):
            for update in chunk["data"].values():
                for message in (update or {}).get("messages", []):
                    for kind, text in steps_of(message):
                        body = {"thread_id": thread_id, "kind": kind, "text": text}
                        client.post(f"/api/claims/{claim_id}/steps", json=body)
                        reply = text if kind == "message" else reply
    return reply
