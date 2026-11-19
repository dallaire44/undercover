import re
from pathlib import Path

BACKEND = Path(__file__).parents[1]


def test_only_main_answers_in_http():
    for path in BACKEND.glob("*.py"):
        if path.name != "main.py":
            assert "HTTPException" not in path.read_text(encoding="utf-8"), path.name


def test_the_backend_never_imports_the_agent():
    for path in BACKEND.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^(from|import) agent\b", text, re.MULTILINE), path.name


def test_only_agent_service_reaches_the_agent():
    for path in BACKEND.glob("*.py"):
        if path.name != "agent_service.py":
            assert "httpx" not in path.read_text(encoding="utf-8"), path.name
