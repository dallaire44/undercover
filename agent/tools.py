"""The agent's tools: one backend call each."""

from typing import Literal

from langchain_core.tools import tool

from agent import api


def call(
    method: str, path: str, body: dict | None = None, params: dict | None = None
) -> str:
    """Call the backend. A refusal comes back as text for the model to read."""
    with api.backend() as client:
        response = client.request(method, path, json=body, params=params)
    if response.is_client_error:
        return f"Refused ({response.status_code}): {response.json()['detail']}"
    response.raise_for_status()
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get one claim in full: its story, items and documents."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy with its plan, trip and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's name and earlier claims."""
    return call("GET", f"/api/customers/{customer_id}/history")


@tool
def list_sections() -> str:
    """List the sections of the policy wording and the claims manual."""
    return call("GET", "/api/documents")


@tool
def search_documents(query: str) -> str:
    """Find the sections of the wording and the manual that match a few words."""
    return call("GET", "/api/documents/search", params={"query": query})


@tool
def read_section(
    document: Literal["policy_wording", "claims_manual"], number: str
) -> str:
    """Read one section of the policy wording or the claims manual, such as 9."""
    return call("GET", f"/api/documents/{document}/sections/{number}")


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim. The payout is 0 unless you approve."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return call("POST", f"/api/claims/{claim_id}/decision", body)


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim exactly the amount of its payout."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    list_sections,
    search_documents,
    read_section,
    record_decision,
    pay_claim,
]
