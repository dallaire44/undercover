"""The agent's service, as the backend calls it: the backend's only way to the agent.

Each call asks the agent to do some work in the background and says whether the
agent took the request. A sign-off or a run stands even if the agent can't be reached.
"""

import logging
import os

import httpx

log = logging.getLogger(__name__)


def agent() -> httpx.Client:
    """Return a client for the agent's service at UNDERCOVER_AGENT."""
    url = os.getenv("UNDERCOVER_AGENT", "http://127.0.0.1:8002")
    return httpx.Client(base_url=url, timeout=10)


def ask(path: str) -> bool:
    """Ask the agent to do some work, and say whether it took the request."""
    try:
        with agent() as client:
            client.post(path).raise_for_status()
    except httpx.HTTPError as error:
        log.warning("The agent's service did not take %s: %s", path, error)
        return False
    return True


def work_run(run_id: str) -> bool:
    return ask(f"/runs/{run_id}")


def work_one(run_id: str, claim_id: str) -> bool:
    return ask(f"/runs/{run_id}/claims/{claim_id}")


def resume_claim(claim_id: str) -> bool:
    return ask(f"/claims/{claim_id}/resume")
