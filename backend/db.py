"""The SQLite database: its tables, and a seed from `data/`."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent.parent / "data"

DOCUMENTS = {
    "claims": "claim_id",
    "policies": "policy_id",
    "customers": "customer_id",
    "handlers": "handler_id",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY, status TEXT NOT NULL, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handlers (handler_id TEXT PRIMARY KEY, doc TEXT NOT NULL);
"""


def connect() -> sqlite3.Connection:
    """Open the database named by UNDERCOVER_DB, or undercover.db."""
    conn = sqlite3.connect(
        os.getenv("UNDERCOVER_DB", "undercover.db"),
        timeout=30,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """Give a request its own connection. Writes commit themselves."""
    with closing(connect()) as conn:
        yield conn


def load(name: str) -> Any:
    """Read one JSON file from `data/`."""
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def seed(conn: sqlite3.Connection) -> None:
    """Copy the claims, policies, customers and handlers from `data/`."""
    with conn:
        for table, key in DOCUMENTS.items():
            for record in load(table):
                values = [record[key], json.dumps(record)]
                if table == "claims":
                    values.insert(1, "waiting")
                marks = ",".join("?" * len(values))
                conn.execute(f"INSERT INTO {table} VALUES ({marks})", values)  # noqa: S608


def init() -> None:
    """Create the tables, and seed them if the database is new."""
    with closing(connect()) as conn:
        conn.executescript(SCHEMA)
        if not conn.execute("SELECT 1 FROM claims").fetchone():
            seed(conn)


def reset() -> None:
    """Drop every table and seed the database again."""
    with closing(connect()) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (name,) in tables.fetchall():
            conn.execute(f"DROP TABLE {name}")  # noqa: S608
    init()
