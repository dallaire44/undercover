"""Rebuild the database from `data/`: `uv run -m backend.seed`."""

from backend import db

if __name__ == "__main__":
    db.reset()
    print("Database rebuilt from data/.")
