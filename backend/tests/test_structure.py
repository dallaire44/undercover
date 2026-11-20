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


def test_only_usage_records_model_calls_and_work_times():
    for path in BACKEND.glob("*.py"):
        if path.name not in {"db.py", "usage.py"}:
            text = path.read_text(encoding="utf-8")
            assert "model_calls" not in text, path.name
            assert "work_times" not in text, path.name


def test_only_agent_service_knows_the_agent_s_address_and_routes():
    for path in BACKEND.glob("*.py"):
        if path.name != "agent_service.py":
            text = path.read_text(encoding="utf-8")
            assert "8002" not in text, path.name
            assert not re.search(r"[\"']/(dispatches|claims/)", text), path.name


ANSWER_KEY = re.compile(r"[.\"']answers\b|\banswers\.|import [^\n]*\banswers\b")


def test_only_scores_reads_the_answer_key():
    for path in BACKEND.glob("*.py"):
        if path.name not in {"db.py", "scores.py"}:
            text = path.read_text(encoding="utf-8")
            assert not ANSWER_KEY.search(text), path.name
