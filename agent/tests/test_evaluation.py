from agent import harness, service
from agent.tests.conftest import dispatch_id


def evaluate(client, claim_set, tiny, agents=5):
    body = {"agents": agents, "claim_set": claim_set, "tiny": tiny}
    assert client.post("/api/evaluations/start", json=body).status_code == 202
    return client.get("/api/evaluations").json()[0]


def test_an_evaluation_leaves_the_queue_as_it_was(client, service, script):
    before = client.get("/api/claims").json()
    evaluation = evaluate(client, "evaluation", False)
    assert evaluation["run"]["status"] == "finished"
    assert len(evaluation["claims"]) == 25
    assert {c["status"] for c in evaluation["claims"]} == {"decided"}
    assert client.get("/api/claims").json() == before
    assert evaluation["scores"]["cost_per_claim"] > 0


def test_a_held_approval_counts_as_finished_and_its_thread_is_cleared(
    client, service, script
):
    held = "RUN-0001-CLM-1112"
    script.decisions[held] = ("approve", 1680.0)
    evaluation = evaluate(client, "held_out", True)
    run = evaluation["run"]
    assert (run["status"], run["claim_set"], run["tiny"]) == (
        "finished",
        "held_out",
        True,
    )
    copy = client.get(f"/api/claims/{held}").json()
    assert copy["status"] == "awaiting_sign_off"
    saved = harness.memory().get_tuple(
        {"configurable": {"thread_id": copy["thread_id"]}}
    )
    assert saved is None
    others = [c for c in run["claims"] if c["claim_id"] != held]
    assert all(
        harness.memory().get_tuple({"configurable": {"thread_id": c["thread_id"]}})
        for c in others
    )


def test_an_evaluation_stopped_by_a_restart_shows_stopped(client, script):
    body = {
        "agents": 5,
        "claim_set": "held_out",
        "tiny": True,
        "model": "stub",
        "reasoning_effort": "none",
    }
    run_id = client.post("/api/evaluations", json=body).json()["run_id"]
    client.post(f"/api/runs/{run_id}/claims/{run_id}-CLM-1104")
    service.stop_left_running()
    evaluation = client.get(f"/api/evaluations/{run_id}").json()
    assert evaluation["run"]["status"] == "stopped"
    later = dispatch_id(client)
    to_work = client.get(f"/api/runs/{later}/claims-to-work").json()
    assert not [c for c in to_work if c["copy_of"]]
