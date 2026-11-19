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
