"""Evaluations: copies of a labelled set's claims, worked like a dispatch and scored.

Each copy gets a new id, such as `RUN-0007-CLM-1001`, written into its record too.
Copies never show in the queue.
"""

from typing import Any

from sqlalchemy import Connection, insert, select

from backend import runs, scores
from backend.db import claims, held_out_claims
from backend.errors import NotFound
from backend.models import Evaluation, EvaluationRequest, LabelledSet, Run


def original(conn: Connection, claim_set: LabelledSet, claim_id: str) -> dict[str, Any]:
    """Return the record of a claim in a labelled set."""
    table = claims if claim_set == "evaluation" else held_out_claims
    query = select(table.c.doc).where(table.c.claim_id == claim_id)
    return conn.execute(query).scalar_one()


def create(conn: Connection, request: EvaluationRequest) -> Run:
    """Create an evaluation and its copies of the set's claims, all waiting."""
    run_id = runs.create(conn, {"kind": "evaluation", **request.model_dump()})
    for claim_id in scores.labelled(conn, request.claim_set, request.tiny):
        copy_id = f"{run_id}-{claim_id}"
        record = original(conn, request.claim_set, claim_id)
        conn.execute(
            insert(claims).values(
                claim_id=copy_id,
                status="waiting",
                doc={**record, "claim_id": copy_id},
                attempts=0,
                run_id=run_id,
                copy_of=claim_id,
            )
        )
    conn.commit()
    return runs.get(conn, run_id)


def get(conn: Connection, run_id: str) -> Evaluation:
    """Return an evaluation with its measures and its scored copies."""
    run = runs.get(conn, run_id)
    if run.kind != "evaluation":
        raise NotFound(f"{run_id} is not an evaluation")
    return scores.score(conn, run)


def list_all(conn: Connection) -> list[Evaluation]:
    """Return every evaluation, newest first."""
    return [get(conn, run_id) for run_id in runs.ids_of(conn, "evaluation")]
