"""The database: its tables and engine, and a seed from `data/`.

The backend uses Supabase Postgres when `DATABASE_URL` is set, and SQLite otherwise.
On Postgres every table is in the `undercover` schema, set as the connection's
search path, so the same queries run on both.
"""

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    URL,
    Column,
    Connection,
    Engine,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    make_url,
    select,
    text,
)

DATA = Path(__file__).parent.parent / "data"
SCHEMA = "undercover"
POOL_SIZE = 4

metadata = MetaData()


def documents(name: str, key: str) -> Table:
    """A table of JSON documents from `data/`, keyed by their id."""
    return Table(
        name,
        metadata,
        Column(key, String, primary_key=True),
        Column("doc", JSON, nullable=False),
    )


claims = Table(
    "claims",
    metadata,
    Column("claim_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("doc", JSON, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("run_id", String),
    Column("thread_id", String),
)
policies = documents("policies", "policy_id")
customers = documents("customers", "customer_id")
handlers = documents("handlers", "handler_id")
decisions = Table(
    "decisions",
    metadata,
    Column("claim_id", String, primary_key=True),
    Column("decision", String, nullable=False),
    Column("payout", Float, nullable=False),
    Column("reason", Text, nullable=False),
    Column("policy_section", String, nullable=False),
    Column("decided_at", String, nullable=False),
)
payments = Table(
    "payments",
    metadata,
    Column("claim_id", String, primary_key=True),
    Column("amount", Float, nullable=False),
    Column("paid_at", String, nullable=False),
    Column("signed_off_by", String),
    Column("signed_off_at", String),
)
sign_offs = Table(
    "sign_offs",
    metadata,
    Column("claim_id", String, primary_key=True),
    Column("handler_id", String, nullable=False),
    Column("signed_at", String, nullable=False),
)
steps = Table(
    "steps",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("claim_id", String, nullable=False),
    Column("thread_id", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("created_at", String, nullable=False),
)
runs = Table(
    "runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("cap", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("summary", Text, nullable=False),
    Column("started_at", String, nullable=False),
    Column("finished_at", String),
)
todos = Table(
    "todos",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("position", Integer, primary_key=True),
    Column("content", Text, nullable=False),
    Column("status", String, nullable=False),
)

DOCUMENTS = {
    "claims": claims,
    "policies": policies,
    "customers": customers,
    "handlers": handlers,
}


def url() -> URL:
    """Return Supabase's URL from DATABASE_URL, or SQLite's at UNDERCOVER_DB."""
    found = os.getenv("DATABASE_URL")
    if found:
        return make_url(found).set(drivername="postgresql+psycopg")
    return make_url(f"sqlite:///{os.getenv('UNDERCOVER_DB', 'undercover.db')}")


@cache
def engine_for(address: URL) -> Engine:
    """Make the engine for one database, with at most 4 connections on Postgres."""
    if address.get_backend_name() == "postgresql":
        return create_engine(
            address,
            pool_size=POOL_SIZE,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"options": f"-c search_path={SCHEMA}"},
        )
    return create_engine(address, connect_args={"check_same_thread": False})


def engine() -> Engine:
    """Return the engine for the database in the environment."""
    return engine_for(url())


def connect() -> Connection:
    """Open a connection. Writes commit themselves."""
    return engine().connect()


def get_db() -> Iterator[Connection]:
    """Give a request its own connection."""
    with connect() as conn:
        yield conn


def now() -> str:
    """Return the current time, to the second, as stored in the database."""
    return datetime.now(UTC).isoformat(timespec="seconds")


@cache
def load(name: str) -> Any:
    """Read one JSON file from `data/`, once."""
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def seed(conn: Connection) -> None:
    """Copy the claims, policies, customers and handlers from `data/`."""
    for name, table in DOCUMENTS.items():
        key = next(iter(table.primary_key)).name
        rows = [{key: record[key], "doc": record} for record in load(name)]
        if table is claims:
            rows = [{**r, "status": "waiting", "attempts": 0} for r in rows]
        conn.execute(insert(table), rows)


def init() -> None:
    """Create the tables, and seed them if the database is new."""
    with engine().begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        metadata.create_all(conn)
        if conn.execute(select(claims.c.claim_id).limit(1)).first() is None:
            seed(conn)


def reset() -> None:
    """Drop every table and seed the database again.

    On Postgres this drops the whole schema, so the agent's saved threads go with
    our tables, and no run after a reseed carries on a thread from before it.
    """
    with engine().begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        else:
            metadata.drop_all(conn)
    init()
