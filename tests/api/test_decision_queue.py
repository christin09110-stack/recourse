"""The queue of parked questions, and what each one has to say for itself.

A question a person cannot act on is not a question. The policy stops one specific
call about one specific denial, and Muster shipped a console that rendered that as a
rule sentence with an em dash where the claim belongs — three statements about a
subject the screen did not know.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from recourse.api.app import create_app

from .conftest import SpyRunner, paused_on


def _client(resumer: SpyRunner) -> TestClient:
    return TestClient(create_app(
        watch_runner=SpyRunner(paused_on()),
        press_runner=SpyRunner(),
        decision_resumer=resumer,
    ))


def _park(client: TestClient) -> str:
    body = client.post("/api/triage").json()
    assert body["status"] == "awaiting_decision"
    return body["decision_id"]


def test_a_paused_run_becomes_a_question_that_names_its_claim():
    resumer = SpyRunner()
    client = _client(resumer)
    decision_id = _park(client)

    (pending,) = client.get("/api/decisions").json()
    assert pending["decision_id"] == decision_id
    assert pending["rule"] == "uncited_clinical_assertion"
    # The question has to say which denial it is about. Muster's asked the operator
    # to approve a rule sentence with an em dash where the subject belongs.
    assert pending["subject"]["denial_id"] == "den-50"
    assert pending["subject"]["provider"] == "Silver Creek Home Health"
    assert pending["proposal"]["tool"] == "draft_letter_body"


def test_an_approval_that_pauses_again_becomes_a_second_question():
    resumer = SpyRunner(paused_on(denial_id="den-197", rule="deadline_at_risk"))
    client = _client(resumer)
    first = _park(client)
    body = client.post(f"/api/decisions/{first}/answer", json={
        "outcome": "approve", "by": "Marcus Reyes", "role": "spouse", "note": "",
    }).json()

    assert body["status"] == "awaiting_decision"
    assert body["decision_id"] != first
    (pending,) = client.get("/api/decisions").json()
    assert pending["subject"]["denial_id"] == "den-197"


def test_answering_a_decision_that_is_not_pending_is_a_404():
    client = _client(SpyRunner())
    assert client.post("/api/decisions/dec-nope/answer", json={
        "outcome": "approve", "by": "x", "role": "self", "note": "",
    }).status_code == 404
