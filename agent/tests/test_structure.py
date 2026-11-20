import re
from pathlib import Path

AGENT = Path(__file__).parents[1]


def modules_except(name):
    return [p for p in AGENT.glob("*.py") if p.name != name]


def test_only_api_reaches_the_backend():
    for path in modules_except("api.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[\"']/api/", text), path.name
        assert "httpx" not in text, path.name


def test_every_tool_is_in_tools():
    for path in modules_except("tools.py"):
        assert "@tool" not in path.read_text(encoding="utf-8"), path.name


def test_only_the_harness_saves_checkpoints():
    for path in modules_except("harness.py"):
        assert "langgraph.checkpoint" not in path.read_text(encoding="utf-8"), path.name


def test_only_the_service_answers_in_http():
    for path in modules_except("service.py"):
        assert "fastapi" not in path.read_text(encoding="utf-8"), path.name


def test_the_dispatcher_reaches_the_claim_agent_only_through_work_claim():
    text = (AGENT / "dispatcher.py").read_text(encoding="utf-8")
    assert "agent.tools" not in text
    assert not re.search(r"from agent import .*\btools\b", text)
    assert set(re.findall(r"harness\.(\w+)", text)) == {"work_claim"}


def test_the_agent_never_asks_for_the_answer_key():
    for path in AGENT.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "/api/evaluations/{" not in text, path.name
        assert not re.search(r"[.\"'/]answers\b|\banswers\.", text), path.name
