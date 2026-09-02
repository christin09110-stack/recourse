"""Answering a decision, and the one rule that must hold whatever the SDK does.

Muster resumed the run on *any* answer and trusted the Strands `evaluate` callback to
refuse the paused tool call on a decline. Against the deployed service that refusal
did not hold: the operator declined, the resumed run did the thing anyway, and the
receipt carried the name of the person who had refused it.

So the assertion here is not "the resumed run behaved". It is that the resumer is
never called at all. A spy that records its calls is the only way to assert a thing
did not happen.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from recourse.api.app import create_app

from .conftest import FakeResult, SpyRunner, paused_on


def _client(resumer: SpyRunner, watch: SpyRunner | None = None) -> TestClient:
    return TestClient(create_app(
        watch_runner=watch or SpyRunner(paused_on()),
        press_runner=SpyRunner(),
        decision_resumer=resumer,
    ))


def _park(client: TestClient) -> str:
    body = client.post("/api/triage").json()
    assert body["status"] == "awaiting_decision"
    return body["decision_id"]


def test_a_decline_never_reaches_the_resumer_and_changes_nothing():
    resumer = SpyRunner()
    client = _client(resumer)
    before = client.get("/api/appeals").json()
    decision_id = _park(client)

    answer = client.post(f"/api/decisions/{decision_id}/answer", json={
        "outcome": "decline", "by": "Adaeze Okafor", "role": "self",
        "note": "the surgeon has not written the letter yet",
    })

    assert answer.status_code == 200
    body = answer.json()
    assert body["status"] == "declined"
    assert body["changed"] is False
    assert resumer.calls == [], "a decline must never be handed back to the agent"
    assert client.get("/api/appeals").json() == before
    assert client.get("/api/decisions").json() == []


def test_a_decline_is_written_into_the_record_with_the_person_who_made_it():
    client = _client(SpyRunner())
    decision_id = _park(client)
    client.post(f"/api/decisions/{decision_id}/answer", json={
        "outcome": "decline", "by": "Adaeze Okafor", "role": "self", "note": "",
    })
    answered = [e for e in client.get("/api/journal").json()
                if e["kind"] == "decision_answered"]
    assert len(answered) == 1
    assert answered[0]["decided_by"] == "Adaeze Okafor"
    assert "declined" in answered[0]["sentence"]


def test_an_approval_does_reach_the_resumer():
    resumer = SpyRunner(FakeResult(text="drafted the letter body"))
    client = _client(resumer)
    decision_id = _park(client)

    body = client.post(f"/api/decisions/{decision_id}/answer", json={
        "outcome": "approve", "by": "Marcus Reyes", "role": "spouse", "note": "",
    }).json()

    assert len(resumer.calls) == 1
    state, pending = resumer.calls[0]
    assert pending.decision.decision_id == decision_id
    assert pending.decision.by == "Marcus Reyes"
    assert pending.interrupt_id.startswith("v1:before_tool_call:")
    assert body == {"status": "done", "changed": True, "text": "drafted the letter body"}
