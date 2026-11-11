"""Start a run through the API and follow it until it ends."""

import argparse
import time

from agent import api

POLL_SECONDS = 2.0


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """Read `--cap 5` or `--claim CLM-1001` from the command line."""
    parser = argparse.ArgumentParser(
        prog="uv run -m agent", description="Start a run of the agent and follow it."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--cap", type=int, help="work up to this many waiting claims")
    target.add_argument("--claim", help="work one waiting claim, such as CLM-1001")
    return parser.parse_args(argv)


def start(args: argparse.Namespace) -> str:
    """Start the run, and return its id. A refusal ends the program with its reason."""
    try:
        run = api.start_agent(args.claim) if args.claim else api.start_run(args.cap)
    except api.Refused as refusal:
        raise SystemExit(f"Refused: {refusal.detail}") from refusal
    return run["run_id"]


def follow(run_id: str) -> str:
    """Print the run's to-do list as it changes, then return how the run ended."""
    shown = ""
    while True:
        run = api.get_run(run_id)
        todos = "\n".join(f"[{t['status']}] {t['content']}" for t in run["todos"])
        if todos != shown:
            print(todos + "\n")
            shown = todos
        if run["status"] != "running":
            return f"{run_id} {run['status']}: {run['summary']}"
        time.sleep(POLL_SECONDS)


def main(argv: list[str] | None = None) -> None:
    """Start a run from the command line and follow it to the end."""
    print(follow(start(parse(argv))))
