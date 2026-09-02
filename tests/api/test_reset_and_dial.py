"""The reset, the dial, and the record.

The reset is tested against a *dirtied* console rather than a fresh one. Muster's
reset rebuilt its state a second way and forgot the seeding start-up did, so the
console it produced was not the console a cold start produces — every control was
refused, and nothing said why. Asserting "reset returns 200" would have passed.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from recourse.api.app import create_app

from .conftest import SpyRunner, paused_on


def _dirty(client: TestClient) -> None:
    """Leave marks: a parked decision, an upload in the journal, a moved dial."""
    client.post("/api/triage")
    client.post("/api/eob", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    client.put("/api/autonomy", json={"level": "trusted"})


def test_the_reset_restores_the_seeded_world():
    client = TestClient(create_app(
        watch_runner=SpyRunner(paused_on()),
        press_runner=SpyRunner(),
        decision_resumer=SpyRunner(),
    ))
    fresh_case = client.get("/api/case").json()
    fresh_journal = client.get("/api/journal").json()
    fresh_deadlines = client.get("/api/deadlines").json()

    _dirty(client)
    assert client.get("/api/decisions").json(), "the world under test was not dirtied"

    assert client.post("/api/demo/reset").json()["status"] == "reset"

    assert client.get("/api/decisions").json() == []
    assert client.get("/api/case").json() == fresh_case
    assert client.get("/api/journal").json() == fresh_journal
    # The dial is the operator's setting, not part of the demo world, so it stays
    # where they put it. Silently returning it to the default between two takes of
    # a recording would be a change nobody asked for and nobody would see.
    assert client.get("/api/autonomy").json()["level"] == "trusted"
    # Every appeal is back, in the same worst-first order the cold start produced.
    assert [d["appeal_id"] for d in client.get("/api/deadlines").json()] == \
        [d["appeal_id"] for d in fresh_deadlines]


def test_the_journal_opens_on_the_appeals_the_world_already_has_running(client):
    entries = client.get("/api/journal").json()
    assert [e["kind"] for e in entries] == ["appeal_opened"] * 3
    assert {e["appeal_id"] for e in entries} == {"appeal-16", "appeal-50", "appeal-197"}


def test_the_journal_exports_as_a_file_somebody_can_open(client):
    response = client.get("/api/journal.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "filename=journal.csv" in response.headers["content-disposition"]
    header, *rows = response.text.strip().splitlines()
    assert header.startswith("at,kind,sentence")
    assert len(rows) == 3


def test_the_dial_carries_the_three_rules_it_cannot_move(client):
    body = client.get("/api/autonomy").json()
    assert body["non_negotiable_rules"] == [
        "deadline_at_risk", "filing_is_not_the_agents", "uncited_clinical_assertion",
    ]
    # Every level warns about deadlines. A setting that made Recourse quieter about
    # a closing window would be a setting that made it useless.
    for level in body["levels"]:
        moved = client.put("/api/autonomy", json={"level": level}).json()
        assert moved["thresholds"]["warn_days"] >= 30
