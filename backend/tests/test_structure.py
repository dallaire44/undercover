from pathlib import Path

BACKEND = Path(__file__).parents[1]


def test_only_main_answers_in_http():
    for path in BACKEND.glob("*.py"):
        if path.name != "main.py":
            assert "HTTPException" not in path.read_text(encoding="utf-8"), path.name
