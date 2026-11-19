import pytest

from agent import cli
from agent.tests.conftest import decide, dispatch_id


def test_one_claim_from_the_command_line(client, service, script, capsys):
    script.decisions["CLM-1003"] = ("approve", 3750.0)
    cli.main(["CLM-1003"])
    assert capsys.readouterr().out == (
        "CLM-1003: awaiting sign off\n"
        "RUN-0001 finished.\n"
        "Approved 1, declined 0, referred 0.\n"
        "Waiting for sign-off: CLM-1003, $3,750.00\n"
    )


def test_a_claim_left_for_a_handler(client, service, script, capsys):
    script.errors["CLM-1001"] = [RuntimeError("the model broke")] * 2
    cli.main(["CLM-1001"])
    assert capsys.readouterr().out.endswith(
        "RUN-0001 finished.\n"
        "Approved 0, declined 0, referred 0.\n"
        "Left for a handler: CLM-1001\n"
    )


def test_how_a_stopped_run_ended(client):
    run_id = dispatch_id(client)
    client.post(f"/api/runs/{run_id}/claims/CLM-1001")
    reason = {"reason": "The agent's service restarted"}
    client.post(f"/api/runs/{run_id}/stop", json=reason)
    assert cli.ending(client.get(f"/api/runs/{run_id}").json()) == (
        "RUN-0001 stopped: The agent's service restarted\n"
        "Approved 0, declined 0, referred 0.\n"
        "Still in progress: CLM-1001"
    )


def test_the_command_line_needs_one_claim(capsys):
    for argv in ([], ["CLM-1001", "CLM-1002"], ["--cap", "5"]):
        with pytest.raises(SystemExit):
            cli.parse(argv)
    assert "usage: uv run -m agent" in capsys.readouterr().err


def test_the_command_line_shows_a_refusal(client, service):
    decide(client, "CLM-1001")
    with pytest.raises(SystemExit, match="Refused: CLM-1001 is not waiting"):
        cli.start("CLM-1001")
