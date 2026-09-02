"""The read routes: the world, the case file, the denials and the clocks.

The frozen clock is asserted rather than assumed. Every countdown in the console is
measured from `GET /api/world`, and a browser that stamped `new Date()` instead would
show one set of figures in a recording and different ones on playback.
"""

from __future__ import annotations

from recourse.adapters.frozen import FROZEN_TODAY


def test_health_is_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_the_world_exposes_the_frozen_clock_and_the_dial(client):
    world = client.get("/api/world").json()
    assert world["now"] == FROZEN_TODAY.isoformat()
    assert world["now_at"].startswith(FROZEN_TODAY.isoformat())
    assert world["autonomy"] == "balanced"
    assert {p["plan_type"] for p in world["plans"]} == {"aca_marketplace", "erisa_group_health"}


def test_every_plan_carries_its_cited_clock_table(client):
    for plan in client.get("/api/world").json()["plans"]:
        rules = plan["rules"]
        assert rules["in_scope"], plan["plan_id"]
        assert rules["time_to_appeal"] == "180 days"
        assert rules["time_to_appeal_citation"].startswith("https://")


def test_the_case_file_holds_the_episode(client):
    case = client.get("/api/case").json()
    assert case["case_id"] == "case-okafor-reyes"
    assert len(case["claims"]) == 5
    assert len(case["denial_ids"]) == 4
    # Money crosses as a string, never a float the browser would have to divide.
    line = case["claims"][0]["lines"][0]
    assert isinstance(line["billed"], str) and "." in line["billed"]


def test_denials_carry_their_class_their_code_and_their_gaps(client):
    denials = {d["denial_id"]: d for d in client.get("/api/denials").json()}

    clerical = denials["den-16"]
    assert clerical["denial_class"] == "clerical"
    assert clerical["matched_code"] == "16"
    assert clerical["citation"].startswith("https://x12.org/")
    assert clerical["gaps"] == []
    assert clerical["can_prepare_alone"] is True

    # The authorisation approval has been in the file since before the scan, so
    # nothing is missing — and it is still not a clinical judgement, so it can be
    # prepared alone.
    assert denials["den-197"]["gaps"] == []
    assert denials["den-197"]["can_prepare_alone"] is True

    # The one the agent hands back. There is no clinician letter, and there is not
    # supposed to be: the argument is the surgeon's to make.
    clinical = denials["den-50"]
    assert clinical["denial_class"] == "clinical"
    assert [gap["kind"] for gap in clinical["gaps"]] == ["clinical_note"]
    assert clinical["can_prepare_alone"] is False


def test_deadlines_come_back_worst_first_with_the_day_150_appeal_on_them(client):
    deadlines = client.get("/api/deadlines").json()
    order = {"missed": 0, "critical": 1, "approaching": 2, "ok": 3}
    assert [order[d["risk"]] for d in deadlines] == sorted(order[d["risk"]] for d in deadlines)

    by_id = {d["appeal_id"]: d for d in deadlines}
    # Day 150 of 180: thirty days left, and the sentence says so in plain words.
    assert by_id["appeal-50"]["days_remaining"] == 30
    assert by_id["appeal-50"]["risk"] == "approaching"
    assert "30 days left to appeal" in by_id["appeal-50"]["sentence"]
    # The other clock: the one running against the insurer.
    assert by_id["appeal-16"]["insurer_overdue"] is True
    assert "19 days past its own deadline" in by_id["appeal-16"]["sentence"]


def test_an_appeal_carries_its_levels_and_both_clocks(client):
    appeals = {a["appeal_id"]: a for a in client.get("/api/appeals").json()}
    appeal = appeals["appeal-16"]
    assert appeal["levels"] and appeal["history"] == []
    assert appeal["deadlines"]["mine"] and appeal["deadlines"]["theirs"]
    assert appeal["deadlines"]["citation"].startswith("https://")
