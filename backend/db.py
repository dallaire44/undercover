"""SQLite storage: connect, create the tables and seed them from data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY, data TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (
    claim_id TEXT PRIMARY KEY, decision TEXT NOT NULL, payout REAL NOT NULL,
    reason TEXT NOT NULL, policy_section TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments (
    claim_id TEXT PRIMARY KEY, amount REAL NOT NULL, paid_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sign_offs (
    claim_id TEXT PRIMARY KEY, handler_id TEXT NOT NULL, signed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT, claim_id TEXT NOT NULL,
    thread_id TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
    created_at TEXT NOT NULL);
"""

DOCUMENTS = [
    ("claims", "claim_id"),
    ("policies", "policy_id"),
    ("customers", "customer_id"),
    ("handlers", "handler_id"),
]


def db_path() -> str:
    """The database file, from UNDERCOVER_DB or undercover.db."""
    return os.getenv("UNDERCOVER_DB", "undercover.db")


def seed(conn: sqlite3.Connection) -> None:
    """Copy the JSON records in data/ into the tables. Every claim starts waiting."""
    for table, key in DOCUMENTS:
        for record in json.loads((DATA / f"{table}.json").read_text()):
            columns = "?, ?, 'waiting'" if table == "claims" else "?, ?"
            conn.execute(
                f"INSERT INTO {table} VALUES ({columns})",  # noqa: S608
                (record[key], json.dumps(record)),
            )
    conn.commit()


def connect() -> sqlite3.Connection:
    """Open the database, creating and seeding it on first use."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if conn.execute("SELECT 1 FROM claims").fetchone() is None:
        seed(conn)
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """A connection for one request, closed afterwards."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
