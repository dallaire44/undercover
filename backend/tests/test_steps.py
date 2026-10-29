def add(client, text, kind="message", claim_id="CLM-1001"):
    body = {"thread_id": "t1", "kind": kind, "text": text}
    return client.post(f"/api/claims/{claim_id}/steps", json=body)


def test_steps_come_back_oldest_first(client):
    add(client, "first")
    add(client, "second", kind="tool_call")
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [s["text"] for s in steps] == ["first", "second"]
    assert steps[1]["kind"] == "tool_call"
    assert steps[0]["thread_id"] == "t1"


def test_step_kind_must_be_valid(client):
    assert add(client, "x", kind="shout").status_code == 422


def test_steps_of_an_unknown_claim(client):
    assert add(client, "x", claim_id="CLM-9999").status_code == 404
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404
