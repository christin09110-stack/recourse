"""What the PRESS tools do with the clock, an answer and a notice.

Which stage follows an upheld appeal is its own file: `test_stages.py`.

The one with teeth here is the missing date. An appeal marked upheld with no date
leaves the level above it permanently unable to compute a deadline, so the countdown
that is the entire product never starts and nothing complains.
"""

from __future__ import annotations

from recourse.adapters.frozen import DAYS_INTO_FILING_WINDOW, INSURER_OVERDUE_BY
from recourse.domain.types import Outcome
from tests.loops.support import press

ANSWERED = "2026-09-01"


def test_the_sweep_finds_the_day_150_appeal_and_the_silent_insurer():
    _, tools, _ = press()
    rows = {row["appeal_id"]: row for row in tools["sweep_deadlines"]()}
    assert rows["appeal-50"]["risk"] == "approaching"
    assert rows["appeal-50"]["days_remaining"] == 180 - DAYS_INTO_FILING_WINDOW
    assert rows["appeal-16"]["insurer_overdue"] is True
    assert f"{INSURER_OVERDUE_BY} days past" in rows["appeal-16"]["sentence"]


def test_the_sweep_puts_the_worst_first():
    _, tools, _ = press()
    rows = tools["sweep_deadlines"]()
    assert rows[0]["appeal_id"] == "appeal-50"


def test_an_answer_with_no_date_is_refused_and_says_why_the_date_matters():
    """The store raises; the tool surfaces it. Without the date the next level's
    clock never starts, and nothing complains."""
    store, tools, _ = press()
    result = tools["record_response"](appeal_id="appeal-16", outcome="upheld")
    assert "error" in result
    assert "clock starts" in result["error"]
    assert store.appeal("appeal-16").outcome is Outcome.PENDING


def test_an_outcome_that_is_not_an_answer_is_refused():
    _, tools, _ = press()
    assert "error" in tools["record_response"](appeal_id="appeal-16", outcome="pending",
                                               answered_on=ANSWERED)


def test_advancing_an_unanswered_appeal_is_refused_rather_than_dated():
    _, tools, _ = press()
    result = tools["advance_stage"](appeal_id="appeal-50")
    assert "error" in result and "invent a deadline" in result["error"]


def test_an_overturned_appeal_is_not_advanced_against_its_own_win():
    _, tools, _ = press()
    tools["record_response"](appeal_id="appeal-16", outcome="overturned",
                             answered_on=ANSWERED)
    assert "error" in tools["advance_stage"](appeal_id="appeal-16")


def test_a_notice_carries_the_computed_deadline_and_not_the_models_arithmetic():
    _, tools, notices = press()
    tools["sweep_deadlines"]()
    sent = tools["notify_person"](appeal_id="appeal-50", message="Have you heard back?")
    assert sent["risk"] == "approaching"
    assert "30 days left" in sent["deadline"]
    assert notices[0]["appeal_id"] == "appeal-50"
