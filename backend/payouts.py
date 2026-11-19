"""UnderCover's payout rules for an approved claim.

The rules come from section 10 of the policy wording, the plan limits in
`data/plans.json`, and sections 6, 7 and 10 of the claims manual.
"""

from math import ceil, inf
from typing import Any

from backend import db
from backend.models import Benefit, Payout, PayoutLine, PayoutRequest, PayoutStep

CASH_LIMIT = 100.0
HOTEL_NIGHT_LIMIT = 350.0
MEALS_PER_TRAVELER_PER_DAY = 35.0

BENEFIT_MAXIMUM: dict[Benefit, str] = {
    "trip_cancellation": "trip_cancellation_max",
    "trip_interruption": "trip_cancellation_max",
    "trip_delay": "trip_delay_max",
    "baggage_delay": "baggage_delay_max",
    "baggage": "baggage_max",
    "passport": "passport_max",
    "emergency_medical": "emergency_medical_max",
}

type Policy = dict[str, Any]


def plan(policy: Policy) -> dict[str, Any]:
    """Return the limits of the policy's plan."""
    return next(p for p in db.load("plans")["plans"] if p["plan"] == policy["plan"])


def approval_limit() -> float:
    """Return the payout above which a handler must sign off."""
    return db.load("company")["payout_approval_limit"]


def step(description: str, amount: float) -> PayoutStep:
    """Make one line of the calculation, rounded to the cent."""
    return PayoutStep(step=description, amount=round(amount, 2))


def limit_for(line: PayoutLine, policy: Policy) -> float:
    """Return the most UnderCover pays for one line, or infinity for no limit."""
    per_item = plan(policy)["per_item_limit"]
    travelers = len(policy["travelers"])
    match line.kind:
        case "item":
            return per_item * line.quantity
        case "electronics":
            if "electronics_plus" in policy["add_ons"]:
                add_ons = {a["add_on"]: a for a in db.load("plans")["add_ons"]}
                per_item = add_ons["electronics_plus"]["electronics_per_item_limit"]
            return per_item * line.quantity
        case "hotel":
            return HOTEL_NIGHT_LIMIT * ceil(travelers / 2) * line.nights
        case "meals_without_receipts":
            return MEALS_PER_TRAVELER_PER_DAY * travelers * ceil(line.hours / 24)
        case _:
            return inf


def eligible_amount(line: PayoutLine, policy: Policy) -> PayoutStep:
    """Return the amount claimed for one line, or its limit if that is lower."""
    limit = limit_for(line, policy)
    if line.amount > limit:
        return step(f"{line.description}, limited to ${limit:,.2f}", limit)
    return step(line.description, line.amount)


def benefit_maximum(policy: Policy, benefit: Benefit) -> float:
    """Return the plan's maximum for a benefit, capped at the trip cost for a trip."""
    maximum = plan(policy)[BENEFIT_MAXIMUM[benefit]]
    if benefit in ("trip_cancellation", "trip_interruption"):
        return min(maximum, policy["trip"]["trip_cost"])
    return maximum


def work_out_payout(policy: Policy, request: PayoutRequest) -> Payout:
    """Work out the payout on an approved claim, following wording section 10."""
    lines = request.lines
    calculation = [
        eligible_amount(line, policy) for line in lines if line.kind != "cash"
    ]
    cash = sum(line.amount for line in lines if line.kind == "cash")
    if cash:
        calculation.append(
            step(f"Cash, up to ${CASH_LIMIT:,.0f} in all", min(cash, CASH_LIMIT))
        )
    total = sum(entry.amount for entry in calculation)

    if request.paid_by_others:
        calculation.append(
            step("Less what others have paid or refunded", -request.paid_by_others)
        )
        total -= request.paid_by_others

    if request.benefit in db.load("plans")["deductible_applies_to"] and total > 0:
        deductible = min(plan(policy)["deductible"], total)
        if deductible:
            calculation.append(step("Less the deductible", -deductible))
            total -= deductible

    maximum = benefit_maximum(policy, request.benefit)
    if total > maximum:
        calculation.append(
            step(
                f"Less the amount over the maximum of ${maximum:,.0f}", maximum - total
            )
        )
        total = maximum

    if total < 0:
        calculation.append(step("Nothing is left to pay", -total))
        total = 0.0

    payout = round(total, 2)
    return Payout(
        calculation=calculation,
        payout=payout,
        needs_sign_off=payout > approval_limit(),
    )
