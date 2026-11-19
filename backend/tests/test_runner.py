import httpx
import pytest

from backend import agent_service, runner
from backend.agent_service import ask
from backend.tests.conftest import decide, status


def start(client, cap=2):
    return client.post("/api/runs", json={"cap": cap})


def run_of(client, run_id):
    return client.get(f"/api/runs/{run_id}").json()


def test_a_run_is_handed_to_the_agent(client, agent_calls):
    response = start(client)
    assert response.status_code == 202
    run = response.json()
    assert (run["run_id"], run["cap"], run["status"]) == ("RUN-0001", 2, "running")
    assert agent_calls == ["/runs/RUN-0001"]
    assert run_of(client, "RUN-0001")["status"] == "running"


def test_a_run_the_agent_never_takes_is_stopped(client, monkeypatch):
    monkeypatch.setattr(agent_service, "ask", lambda path: False)
    run = run_of(client, start(client).json()["run_id"])
    assert run["status"] == "stopped"
    assert run["summary"] == runner.UNREACHED
    assert client.post("/api/claims/CLM-1001/agent").status_code == 202
    assert run_of(client, "RUN-0002")["status"] == "stopped"


def test_one_claim_is_handed_to_the_agent(client, agent_calls):
    response = client.post("/api/claims/CLM-1001/agent")
    assert response.status_code == 202
    assert response.json()["cap"] == 1
    assert agent_calls == ["/runs/RUN-0001/claims/CLM-1001"]


def test_one_claim_must_be_waiting(client, agent_calls):
    decide(client, "CLM-1001", "decline", 0.0)
    assert client.post("/api/claims/CLM-1001/agent").status_code == 409
    assert client.post("/api/claims/CLM-9999/agent").status_code == 404
    assert client.get("/api/runs/latest").json() is None
    assert agent_calls == []


def test_a_sign_off_reaches_the_agent_once_it_is_saved(client, monkeypatch):
    seen = []

    def ask_agent(path):
        seen.append((path, status(client, "CLM-1003")))
        return True

    monkeypatch.setattr(agent_service, "ask", ask_agent)
    decide(client, "CLM-1003", payout=3750.0)
    client.post("/api/claims/CLM-1003/sign-off", json={"handler_id": "HND-03"})
    assert seen == [("/claims/CLM-1003/resume", "in_progress")]


def test_a_sign_off_stands_if_the_agent_cannot_be_reached(client, monkeypatch):
    monkeypatch.setattr(agent_service, "ask", lambda path: False)
    decide(client, "CLM-1003", payout=3750.0)
    body = {"handler_id": "HND-03"}
    response = client.post("/api/claims/CLM-1003/sign-off", json=body)
    assert response.status_code == 200
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "in_progress"
    assert claim["sign_off"]["handler_name"] == "Priya Raman"


def refused(request):
    raise httpx.ConnectError("Connection refused")


@pytest.mark.parametrize(
    ("answer", "taken"),
    [
        (lambda request: httpx.Response(202), True),
        (lambda request: httpx.Response(500), False),
        (refused, False),
    ],
)
def test_ask_says_whether_the_agent_took_the_request(monkeypatch, answer, taken):
    transport = httpx.MockTransport(answer)
    client = httpx.Client(transport=transport, base_url="http://agent")
    monkeypatch.setattr(agent_service, "agent", lambda: client)
    assert ask("/claims/CLM-1003/resume") is taken


def test_the_agent_s_address(monkeypatch):
    monkeypatch.delenv("UNDERCOVER_AGENT", raising=False)
    assert str(agent_service.agent().base_url) == "http://127.0.0.1:8002"
    monkeypatch.setenv("UNDERCOVER_AGENT", "http://127.0.0.1:8003")
    assert str(agent_service.agent().base_url) == "http://127.0.0.1:8003"
