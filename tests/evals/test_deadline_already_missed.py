"""A deadline already missed.

This is the one state in the domain that cannot be recovered from. An appeal filed
after the window has closed is not a weaker appeal; the merits stop being read. So
the only thing a system can do here is refuse to soften — and the failure to guard
against is a screen that, six months later, has quietly relaxed a closed window back
into a warning because the arithmetic wrapped round or the sort order changed.

The scenario therefore sweeps the same missed deadline again at one day past, at a
year past, and at eleven years past.
"""

from __future__ import annotations

from datetime import date, timedelta

from recourse.domain.clocks import risk_for
from recourse.domain.types import DeadlineRisk
from recourse.policy.finding import Finding
from tests.evals.support import clocks, seeded

#: The refusal was posted in January 2025, so the 180 days ran out in July 2025 —
#: well before the frozen today the rest of the world is measured from.
LONG_AGO = date(2025, 1, 6)


def _missed():
    _, case = seeded()
    return clocks(case.plans["plan-aca"], started_on=LONG_AGO)


def test_a_window_that_closed_last_year_reports_as_missed():
    deadlines = _missed()
    assert deadlines.mine == LONG_AGO + timedelta(days=180)
    assert risk_for(deadlines, date(2026, 9, 2), warn_days=30) is DeadlineRisk.MISSED


def test_it_never_softens_back_to_a_warning_however_long_it_is_left():
    """Swept the day after it closed, a year later, and eleven years later. Every
    sweep says the same thing, and no warning window and no autonomy setting moves
    it: MISSED is checked before anything else can classify it."""
    deadlines = _missed()
    closed_on = deadlines.mine
    for days_past in (0, 1, 7, 365, 4000):
        for warn_days in (30, 45, 60, 5000):
            assert risk_for(
                deadlines, closed_on + timedelta(days=days_past + 1), warn_days,
            ) is DeadlineRisk.MISSED


def test_the_sentence_a_person_reads_does_not_pretend_there_is_anything_left_to_do():
    """No countdown, no 'act now'. The days-remaining figure is negative and the
    sentence does not quote it, because the number is not the point any more."""
    deadlines = _missed()
    today = date(2026, 9, 2)
    _, case = seeded()
    finding = Finding(
        appeal=case.appeals["appeal-50"], deadlines=deadlines,
        risk=risk_for(deadlines, today, 30),
        days_remaining=(deadlines.mine - today).days,
        insurer_overdue=False, _today=today,
    )
    assert finding.days_remaining < 0
    assert finding.needs_raising is True
    assert finding.sentence == (
        "The window to appeal this has closed. Nothing about the merits matters now."
    )
