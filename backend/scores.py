"""An evaluation's scores against the handlers' decisions, with the measures from the
Week 2 Day 4 lab. This is the only module that reads the answer key.
"""

from sqlalchemy import Connection, RowMapping, select

from backend.db import answers
from backend.models import (
    Evaluation,
    LabelledSet,
    Run,
    RunClaim,
    ScoredClaim,
    Scores,
    Verdict,
)

WRONGFUL_DECLINE = 1500.0
NEEDLESS_REFERRAL = 50.0
PAYOUT_TOLERANCE = 1.0


def labelled(conn: Connection, claim_set: LabelledSet, tiny: bool) -> list[str]:
    """Return the ids of a labelled set's claims, or of its tiny ones."""
    query = select(answers.c.claim_id).where(answers.c.claim_set == claim_set)
    if tiny:
        query = query.where(answers.c.tiny)
    return list(conn.scalars(query.order_by(answers.c.claim_id)))


def mistake_cost(
    decision: Verdict, payout: float, handler_decision: Verdict, handler_payout: float
) -> float:
    """Return what the agent's decision costs UnderCover, against the handler's."""
    if decision == handler_decision:
        return abs(payout - handler_payout) if decision == "approve" else 0.0
    if decision == "decline":
        return WRONGFUL_DECLINE
    if decision == "approve":
        return payout
    return NEEDLESS_REFERRAL


def scored(claim: RunClaim, handler: RowMapping) -> ScoredClaim:
    """Score one copy. A copy the agent didn't decide counts as a referral."""
    decision: Verdict = claim.decision or "refer"
    payout = claim.payout or 0.0
    decision_right = decision == handler["decision"]
    return ScoredClaim(
        claim_id=claim.claim_id,
        copy_of=str(claim.copy_of),
        status=claim.status,
        decision=decision,
        payout=payout,
        handler_decision=handler["decision"],
        handler_payout=handler["payout"],
        decision_right=decision_right,
        right=decision_right and abs(payout - handler["payout"]) <= PAYOUT_TOLERANCE,
        mistake_cost=mistake_cost(
            decision, payout, handler["decision"], handler["payout"]
        ),
        cost=claim.cost,
        seconds=claim.seconds,
    )


def measures(run: Run, claims: list[ScoredClaim]) -> Scores:
    """Return the run's measures: quality, cost and time."""
    count = len(claims)
    return Scores(
        decision_accuracy=sum(c.decision_right for c in claims) / count,
        accuracy=sum(c.right for c in claims) / count,
        cost_of_mistakes=sum(c.mistake_cost for c in claims),
        straight_through=sum(c.decision != "refer" for c in claims) / count,
        cost_per_claim=run.cost / count,
        seconds_per_claim=sum(c.seconds for c in claims) / count,
        run_seconds=run.seconds,
    )


def score(conn: Connection, run: Run) -> Evaluation:
    """Score an evaluation's copies against the handlers' decisions."""
    query = select(answers).where(answers.c.claim_set == run.claim_set)
    key = {row["claim_id"]: row for row in conn.execute(query).mappings()}
    claims = [scored(c, key[str(c.copy_of)]) for c in run.claims]
    return Evaluation(run=run, scores=measures(run, claims), claims=claims)
