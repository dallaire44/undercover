"""Start a run through the API and follow it until it ends."""

import time

from agent import api

POLL_SECONDS = 2.0


def start(target: str) -> str:
    """Start a run capped at `target` claims, or on the one claim `target` names."""
    with api.backend() as client:
        if target.isdigit():
            response = client.post("/api/runs", json={"cap": int(target)})
        else:
            response = client.post(f"/api/claims/{target}/agent")
    response.raise_for_status()
    return response.json()["run_id"]


def follow(run_id: str) -> str:
    """Print the run's to-do list as it changes, then return how the run ended."""
    shown = ""
    with api.backend() as client:
        while True:
            run = client.get(f"/api/runs/{run_id}").json()
            todos = "\n".join(f"[{t['status']}] {t['content']}" for t in run["todos"])
            if todos != shown:
                print(todos + "\n")
                shown = todos
            if run["status"] != "running":
                return f"{run_id} {run['status']}: {run['summary']}"
            time.sleep(POLL_SECONDS)
