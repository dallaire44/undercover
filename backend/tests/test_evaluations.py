import json
from contextlib import closing

import pytest
from sqlalchemy import func, select, update

from backend import db, scores
from backend.tests.conftest import decide

EVALUATION = {"agents": 5, "model": "openai/gpt-6-luna", "reasoning_effort": "low"}
TINY = ["CLM-1007", "CLM-1015", "CLM-1017", "CLM-1020", "CLM-1021"]


def evaluate(client, claim_set="evaluation", tiny=True):
    body = {**EVALUATION, "claim_set": claim_set, "tiny": tiny}
    return client.post("/api/evaluations", json=body).json()


def count(table, *where):
    with closing(db.connect()) as conn:
        query = select(func.count()).select_from(table).where(*where)
        return conn.execute(query).scalar_one()


def test_seeding_keeps_the_answer_key_out_of_the_queue(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {c["status"] for c in claims} == {"waiting"}
    assert count(db.held_out_claims) == 25
    assert count(db.answers) == 50
    assert count(db.answers, db.answers.c.tiny) == 10


def test_an_evaluation_works_its_own_copies(client):
    before = client.get("/api/claims").json()
    run = evaluate(client, "held_out")
    assert (run["kind"], run["claim_set"], run["tiny"], run["agents"]) == (
        "evaluation",
        "held_out",
        True,
        5,
    )
    assert (run["model"], run["reasoning_effort"]) == ("openai/gpt-6-luna", "low")
    run_id = run["run_id"]
    copies = [c["claim_id"] for c in run["claims"]]
    assert copies == [
        f"{run_id}-CLM-1104",
        f"{run_id}-CLM-1106",
        f"{run_id}-CLM-1110",
        f"{run_id}-CLM-1112",
        f"{run_id}-CLM-1114",
    ]
    to_work = client.get(f"/api/runs/{run_id}/claims-to-work").json()
    assert sorted(c["claim_id"] for c in to_work) == copies
    copy = client.get(f"/api/claims/{copies[0]}").json()
    assert (copy["claim_id"], copy["copy_of"], copy["status"]) == (
        copies[0],
        "CLM-1104",
        "waiting",
    )
    assert copy["story"]
    assert client.get("/api/claims").json() == before


def test_a_copy_holds_nothing_from_the_handlers_decisions(client):
    run_id = evaluate(client, "evaluation", tiny=False)["run_id"]
    handlers = json.loads((db.DATA / "evals" / "decisions.json").read_text())
    for answer in handlers:
        found = client.get(f"/api/claims/{run_id}-{answer['claim_id']}")
        original = client.get(f"/api/claims/{answer['claim_id']}").json()
        assert set(found.json()) == set(original)
        assert found.json()["decision"] is None
        for field in ("reason", "tests", "difficulty"):
            assert answer[field] not in found.text


def test_a_copy_cannot_be_signed_off(client):
    copy = f"{evaluate(client)['run_id']}-CLM-1021"
    decide(client, copy, "approve", 1825.0)
    assert client.get(f"/api/claims/{copy}").json()["status"] == "awaiting_sign_off"
    refused = client.post(f"/api/claims/{copy}/sign-off", json={"handler_id": "HND-03"})
    assert refused.status_code == 409
    assert refused.json()["detail"] == "An evaluation's copy can't be signed off"


def record(client, run_id, claim_id, cost, seconds):
    client.post(
        f"/api/claims/{claim_id}/model-calls",
        json={"run_id": run_id, "input_tokens": 1, "output_tokens": 1, "cost": cost},
    )
    client.post(
        f"/api/claims/{claim_id}/work-times",
        json={
            "run_id": run_id,
            "started_at": "2026-11-19T10:00:00",
            "seconds": seconds,
        },
    )


def test_the_measures_match_ones_worked_out_by_hand(client):
    run_id = evaluate(client)["run_id"]
    copy = {claim_id: f"{run_id}-{claim_id}" for claim_id in TINY}
    # The handlers: CLM-1007 approve $50, CLM-1015 decline, CLM-1017 refer,
    # CLM-1020 approve $240, CLM-1021 approve $825.
    decide(client, copy["CLM-1007"], "approve", 50.0)  # right
    decide(client, copy["CLM-1020"], "approve", 260.0)  # $20 off
    decide(client, copy["CLM-1021"], "decline", 0.0)  # wrongful decline
    decide(client, copy["CLM-1015"], "refer", 0.0)  # needless referral
    # CLM-1017 is left undecided, which counts as a referral, as the handler did.
    for claim_id, cost, seconds in [
        ("CLM-1007", 0.02, 10),
        ("CLM-1020", 0.03, 20),
        ("CLM-1021", 0.01, 30),
        ("CLM-1015", 0.04, 40),
        ("CLM-1017", 0.0, 50),
    ]:
        record(client, run_id, copy[claim_id], cost, seconds)
    with closing(db.connect()) as conn:
        conn.execute(
            update(db.runs)
            .where(db.runs.c.run_id == run_id)
            .values(
                status="finished",
                started_at="2026-11-19T10:00:00+00:00",
                finished_at="2026-11-19T10:01:30+00:00",
            )
        )
        conn.commit()

    evaluation = client.get(f"/api/evaluations/{run_id}").json()
    assert evaluation["scores"] == {
        # Decision right on CLM-1007, CLM-1020 and CLM-1017: 3 of 5.
        "decision_accuracy": pytest.approx(0.6),
        # Within a dollar too on CLM-1007 and CLM-1017: 2 of 5.
        "accuracy": pytest.approx(0.4),
        # $20 off, $1,500 for the wrongful decline, $50 for the needless referral.
        "cost_of_mistakes": pytest.approx(1570.0),
        # Not referred: CLM-1007, CLM-1020 and CLM-1021, 3 of 5.
        "straight_through": pytest.approx(0.6),
        # $0.10 over 5 claims.
        "cost_per_claim": pytest.approx(0.02),
        # 150 seconds over 5 claims.
        "seconds_per_claim": pytest.approx(30.0),
        # 10:00:00 to 10:01:30.
        "run_seconds": pytest.approx(90.0),
    }
    by_claim = {c["copy_of"]: c for c in evaluation["claims"]}
    assert by_claim["CLM-1017"]["decision"] == "refer"
    assert by_claim["CLM-1017"]["right"]
    assert by_claim["CLM-1020"]["mistake_cost"] == pytest.approx(20.0)
    assert (by_claim["CLM-1020"]["decision_right"], by_claim["CLM-1020"]["right"]) == (
        True,
        False,
    )
    assert (
        by_claim["CLM-1021"]["handler_decision"],
        by_claim["CLM-1021"]["handler_payout"],
    ) == (
        "approve",
        825.0,
    )


def test_the_evaluations_newest_first(client):
    first = evaluate(client)["run_id"]
    client.post(f"/api/runs/{first}/stop", json={"reason": "Stopped by hand."})
    second = evaluate(client, "held_out")["run_id"]
    listed = client.get("/api/evaluations").json()
    assert [e["run"]["run_id"] for e in listed] == [second, first]
    assert listed[1]["run"]["status"] == "stopped"
    dispatch = {"agents": 3, "model": "m", "reasoning_effort": "none"}
    client.post(f"/api/runs/{second}/stop", json={"reason": "Stopped by hand."})
    later = client.post("/api/dispatches", json=dispatch).json()["run_id"]
    to_work = client.get(f"/api/runs/{later}/claims-to-work").json()
    assert all(c["copy_of"] is None for c in to_work)
    assert len(to_work) == 25
    assert client.get(f"/api/evaluations/{later}").status_code == 404


def test_an_evaluation_is_handed_to_the_agent(client, agent_calls):
    body = {"agents": 5, "claim_set": "held_out", "tiny": True}
    assert client.post("/api/evaluations/start", json=body).status_code == 202
    assert agent_calls == [("/evaluations", body)]
    wrong = {**body, "claim_set": "queue"}
    assert client.post("/api/evaluations/start", json=wrong).status_code == 422


def test_the_cost_of_each_kind_of_mistake():
    assert scores.mistake_cost("approve", 1825.0, "decline", 0.0) == 1825.0
    assert scores.mistake_cost("decline", 0.0, "approve", 825.0) == 1500.0
    assert scores.mistake_cost("refer", 0.0, "decline", 0.0) == 50.0
    assert scores.mistake_cost("approve", 260.0, "approve", 240.0) == 20.0
    assert scores.mistake_cost("decline", 0.0, "decline", 0.0) == 0.0
