"""Read the records: claims, policies, customers and handlers."""

import json
import sqlite3

from fastapi import HTTPException

from backend import db
from backend.models import (
    ClaimDetail,
    ClaimSummary,
    CustomerHistory,
    Handler,
    Policy,
)


def document(conn: sqlite3.Connection, table: str, key: str, value: str) -> dict:
    """Return one stored record, or raise 404."""
    row = conn.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchone()  # noqa: S608
    if row is None:
        raise HTTPException(404, f"{value} not found")
    record = json.loads(row["doc"])
    return {**record, "status": row["status"]} if table == "claims" else record


def _doc(row: sqlite3.Row) -> dict:
    return json.loads(row["doc"])


def customer_name(conn: sqlite3.Connection, customer_id: str) -> str:
    """Return a customer's name."""
    return document(conn, "customers", "customer_id", customer_id)["name"]


def list_claims(conn: sqlite3.Connection) -> list[ClaimSummary]:
    """Return every claim in the queue."""
    customers = conn.execute("SELECT doc FROM customers").fetchall()
    names = {c["customer_id"]: c["name"] for c in map(_doc, customers)}
    rows = conn.execute("SELECT status, doc FROM claims ORDER BY claim_id").fetchall()
    claims = [{**json.loads(row["doc"]), "status": row["status"]} for row in rows]
    return [
        ClaimSummary(**claim, customer_name=names[claim["customer_id"]])
        for claim in claims
    ]


def get_claim(conn: sqlite3.Connection, claim_id: str) -> ClaimDetail:
    """Return one claim in full."""
    claim = document(conn, "claims", "claim_id", claim_id)
    name = customer_name(conn, claim["customer_id"])
    return ClaimDetail(**claim, customer_name=name)


def get_policy(conn: sqlite3.Connection, policy_id: str) -> Policy:
    """Return a policy with the name of its plan."""
    policy = document(conn, "policies", "policy_id", policy_id)
    plans = {p["plan"]: p["name"] for p in db.load("plans")["plans"]}
    return Policy(**{**policy, "plan_name": plans[policy["plan"]]})


def get_history(conn: sqlite3.Connection, customer_id: str) -> CustomerHistory:
    """Return a customer's name and earlier claims, with no contact details."""
    customer = document(conn, "customers", "customer_id", customer_id)
    return CustomerHistory(**customer)


def list_handlers(conn: sqlite3.Connection) -> list[Handler]:
    """Return the claims handlers."""
    rows = conn.execute("SELECT doc FROM handlers ORDER BY handler_id").fetchall()
    return [Handler(**json.loads(row["doc"])) for row in rows]
