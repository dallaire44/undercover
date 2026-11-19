"""The UnderCover backend's API, as the agent calls it: one function per operation."""

import os
from typing import Any, Literal

import httpx

type Json = dict[str, Any]


class Refused(Exception):
    """The backend refused a request (4xx), with its reason."""

    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(f"Refused ({status}): {detail}")
        self.detail = detail


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(
        base_url=os.getenv("BACKEND_URL", "http://localhost:8000"), timeout=30
    )


def send(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Call the backend, raising Refused when it refuses."""
    with backend() as client:
        response = client.request(method, path, **kwargs)
    if response.is_client_error:
        raise Refused(response.status_code, response.json()["detail"])
    response.raise_for_status()
    return response


def get_claim(claim_id: str) -> Json:
    return send("GET", f"/api/claims/{claim_id}").json()


def get_policy(policy_id: str) -> Json:
    return send("GET", f"/api/policies/{policy_id}").json()


def calculate_payout(policy_id: str, request: Json) -> str:
    return send("POST", f"/api/policies/{policy_id}/payout", json=request).text


def get_claim_history(customer_id: str) -> Json:
    return send("GET", f"/api/customers/{customer_id}/history").json()


def list_sections() -> str:
    return send("GET", "/api/documents").text


def search_documents(query: str) -> str:
    return send("GET", "/api/documents/search", params={"query": query}).text


def read_section(document: str, number: str) -> str:
    return send("GET", f"/api/documents/{document}/sections/{number}").text


def get_instructions(agent: Literal["queue", "claim"]) -> str:
    return send("GET", f"/api/instructions/{agent}").text


def record_decision(claim_id: str, decision: Json) -> Json:
    return send("POST", f"/api/claims/{claim_id}/decision", json=decision).json()


def pay_claim(claim_id: str, amount: float) -> Json:
    path = f"/api/claims/{claim_id}/payment"
    return send("POST", path, json={"amount": amount}).json()


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> None:
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    send("POST", f"/api/claims/{claim_id}/steps", json=body)


def start_run(cap: int) -> Json:
    return send("POST", "/api/runs", json={"cap": cap}).json()


def start_agent(claim_id: str) -> Json:
    return send("POST", f"/api/claims/{claim_id}/agent").json()


def get_run(run_id: str) -> Json:
    return send("GET", f"/api/runs/{run_id}").json()


def list_claims_to_work(run_id: str) -> list[Json]:
    return send("GET", f"/api/runs/{run_id}/claims-to-work").json()


def take_claim(run_id: str, claim_id: str) -> Json:
    return send("POST", f"/api/runs/{run_id}/claims/{claim_id}").json()


def return_claim(claim_id: str, thread_id: str, reason: str) -> Json:
    body = {"thread_id": thread_id, "reason": reason}
    return send("POST", f"/api/claims/{claim_id}/return", json=body).json()


def write_todos(run_id: str, todos: list[Json]) -> None:
    send("PUT", f"/api/runs/{run_id}/todos", json={"todos": todos})


def finish_run(run_id: str, summary: str) -> Json:
    path = f"/api/runs/{run_id}/finish"
    return send("POST", path, json={"summary": summary}).json()
