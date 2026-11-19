import time
from datetime import datetime, timedelta

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import select

from agent import harness
from agent.tests.conftest import Recorder, call, dispatch_id, stub
from backend import db


def approve(claim_id, payout):
    return call(
        "record_decision",
        claim_id=claim_id,
        decision="approve",
        payout=payout,
        reason="The wording covers it.",
        policy_section="4. Emergency Medical",
    )


def rows(table, claim_id):
    with db.connect() as conn:
        query = select(table).where(table.c.claim_id == claim_id).order_by(table.c.id)
        return [dict(row) for row in conn.execute(query).mappings()]


@pytest.fixture
def run_id(client):
    return dispatch_id(client)


def test_the_default_model_and_its_settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert harness.model_settings() == ("openai/gpt-6-luna", "low")
    assert (harness.model().model_name, harness.model().reasoning_effort) == (
        "openai/gpt-6-luna",
        "low",
    )
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert harness.model_settings() == ("openrouter/free", "none")
    assert harness.model().reasoning_effort is None


def test_each_model_call_is_recorded_with_its_run(client, run_id):
    replies = [
        call("get_claim", claim_id="CLM-1001"),
        call("get_policy", policy_id="POL-2001"),
        AIMessage(content="Done."),
    ]
    harness.run_claim("CLM-1001", "t1", run_id, stub(*replies))
    calls = rows(db.model_calls, "CLM-1001")
    assert len(calls) == 3
    assert {c["run_id"] for c in calls} == {run_id}
    assert {(c["input_tokens"], c["output_tokens"]) for c in calls} == {(1000, 100)}
    assert sum(c["cost"] for c in calls) == pytest.approx(0.03)


def test_a_wait_for_a_sign_off_is_left_out(client, run_id):
    harness.run_claim("CLM-1003", "t1", run_id, stub(approve("CLM-1003", 3750.0)))
    client.post("/api/claims/CLM-1003/sign-off", json={"handler_id": "HND-03"})
    time.sleep(1)
    harness.run_claim("CLM-1003", "t1", None, Recorder(messages=iter([])))
    assert client.get("/api/claims/CLM-1003").json()["payment"] is not None

    first, resumed = rows(db.work_times, "CLM-1003")
    assert (first["run_id"], resumed["run_id"]) == (run_id, None)
    start = datetime.fromisoformat(first["started_at"])
    end = datetime.fromisoformat(resumed["started_at"]) + timedelta(
        seconds=resumed["seconds"]
    )
    worked = first["seconds"] + resumed["seconds"]
    assert worked <= (end - start).total_seconds() - 1


def test_a_failed_attempt_still_counts(client, run_id):
    class FailsSecond(Recorder):
        def _generate(self, messages, *args, **kwargs):
            if self.seen:
                raise RuntimeError("the model broke")
            return super()._generate(messages, *args, **kwargs)

    model_ = FailsSecond(messages=iter([call("get_claim", claim_id="CLM-1001")]))
    model_.seen.clear()
    with pytest.raises(RuntimeError):
        harness.run_claim("CLM-1001", "t1", run_id, model_)
    assert [c["run_id"] for c in rows(db.model_calls, "CLM-1001")] == [run_id]
    assert [t["run_id"] for t in rows(db.work_times, "CLM-1001")] == [run_id]
