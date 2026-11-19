"""The agent's service, as the backend calls it: the backend's only way to the agent.

A start asks the service to begin a run, which it creates and works in the
background, and is refused with the service's reason or because it can't be reached.
A sign-off stands even if the agent can't be reached to resume the claim.
"""

import logging
import os
from typing import Any

import httpx

from backend.errors import Refused

log = logging.getLogger(__name__)
NOT_RUNNING = "The agent's service is not running"


def agent() -> httpx.Client:
    """Return a client for the agent's service at UNDERCOVER_AGENT."""
    url = os.getenv("UNDERCOVER_AGENT", "http://127.0.0.1:8002")
    return httpx.Client(base_url=url, timeout=10)


def post(path: str, body: dict[str, Any] | None) -> None:
    """Ask the agent to do some work, or raise Refused with why it won't."""
    try:
        with agent() as client:
            response = client.post(path, json=body)
    except httpx.TransportError as error:
        raise Refused(NOT_RUNNING) from error
    if response.status_code == httpx.codes.CONFLICT:
        raise Refused(response.json()["detail"])
    response.raise_for_status()


def start_dispatch(agents: int) -> None:
    post("/dispatches", {"agents": agents})


def work_one(claim_id: str) -> None:
    post(f"/claims/{claim_id}/work", None)


def resume_claim(claim_id: str) -> None:
    """Ask the agent to pick a signed-off claim back up, and log it if it can't."""
    try:
        post(f"/claims/{claim_id}/resume", None)
    except (Refused, httpx.HTTPError) as error:
        log.warning("The agent's service did not resume %s: %s", claim_id, error)
