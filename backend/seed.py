"""Rebuild the database from data/, for a fresh start: uv run -m backend.seed."""

from pathlib import Path

from backend.db import connect, db_path


def reset() -> None:
    """Delete the database file and seed a new one."""
    Path(db_path()).unlink(missing_ok=True)
    connect().close()


if __name__ == "__main__":
    reset()
    print(f"Seeded {db_path()}")
