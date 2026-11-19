"""Work one claim from the command line, through the API, and follow it to the end."""

import argparse
import time

from agent import api

POLL_SECONDS = 2.0


def parse(argv: list[str] | None = None) -> str:
    """Read the claim id, such as CLM-1001, from the command line."""
    parser = argparse.ArgumentParser(
        prog="uv run -m agent", description="Work one waiting claim and follow it."
    )
    parser.add_argument("claim_id", help="a waiting claim, such as CLM-1001")
    return parser.parse_args(argv).claim_id


def latest_id() -> str | None:
    """Return the id of the latest dispatch, or None before the first."""
    latest = api.get_latest_dispatch()
    return latest["run_id"] if latest else None


def start(claim_id: str) -> str:
    """Start a dispatch on the claim and return its id once the service creates it.

    A refusal ends the program with its reason.
    """
    before = latest_id()
    try:
        api.start_agent(claim_id)
    except api.Refused as refusal:
        raise SystemExit(f"Refused: {refusal.detail}") from refusal
    while (run_id := latest_id()) == before:
        time.sleep(POLL_SECONDS)
    return str(run_id)


def ending(run: api.Json) -> str:
    """Describe how a run ended, from its summary."""
    summary = run["summary"]
    lines = [
        f"{run['run_id']} {run['status']}"
        + (f": {run['reason']}" if run["reason"] else "."),
        f"Approved {summary['approved']}, declined {summary['declined']}, "
        f"referred {summary['referred']}.",
    ]
    lines += [
        f"Waiting for sign-off: {held['claim_id']}, ${held['payout']:,.2f}"
        for held in summary["awaiting_sign_off"]
    ]
    lines += [f"Left for a handler: {c}" for c in summary["needs_handler"]]
    lines += [f"Still in progress: {c}" for c in summary["in_progress"]]
    return "\n".join(lines)


def follow(run_id: str) -> str:
    """Print each change to the run's claims, then return how the run ended."""
    shown: dict[str, str] = {}
    while True:
        run = api.get_run(run_id)
        for claim in run["claims"]:
            if shown.get(claim["claim_id"]) != claim["status"]:
                shown[claim["claim_id"]] = claim["status"]
                print(f"{claim['claim_id']}: {claim['status'].replace('_', ' ')}")
        if run["status"] != "running":
            return ending(run)
        time.sleep(POLL_SECONDS)


def main(argv: list[str] | None = None) -> None:
    """Work one claim from the command line and follow it to the end."""
    print(follow(start(parse(argv))))
