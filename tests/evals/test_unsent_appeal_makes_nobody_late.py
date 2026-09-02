"""An unsent appeal does not make the insurer late.

This was a real defect and it is pinned here because of how convincing it looked.
The plan's own clock to answer was counted from the *denial notice* rather than from
the day the appeal was posted, which meant the seeded world reported Harbor Blue as
ninety days past its deadline to answer an appeal that had never left the house. It
showed on the deadline screen as a fact, in the letter as an accusation, and there
was nothing about it that read as a bug.

`appeal-50` is the appeal that would have carried it: drafted, at day 150 of its
180-day window, and deliberately never sent because the argument belongs to a
surgeon whose letter has not come.
"""

from __future__ import annotations

from datetime import timedelta

from recourse.domain.clocks import insurer_is_overdue
from recourse.policy.sweep import sweep
from tests.evals.support import clocks, seeded


def test_the_plan_has_no_deadline_to_answer_a_letter_it_has_never_received():
    """`theirs` is None rather than a date. There is no clock to be past."""
    world, case = seeded()
    appeal = case.appeals["appeal-50"]
    assert appeal.sent_on is None

    deadlines = clocks(
        case.plans["plan-aca"], started_on=appeal.stage_started_on, filed_on=None,
    )
    assert deadlines.mine is not None, "the claimant's own window is running"
    assert deadlines.theirs is None
    assert insurer_is_overdue(deadlines, world.now(), answered_on=None) is False


def test_the_old_defect_would_have_called_the_plan_ninety_days_late():
    """The counterfactual, computed rather than asserted from memory. Feeding the
    notice date in where the filing date belongs produces a deadline three months in
    the past and an insurer squarely in breach of it."""
    world, case = seeded()
    appeal = case.appeals["appeal-50"]

    as_if_filed_at_notice = clocks(
        case.plans["plan-aca"], started_on=appeal.stage_started_on,
        filed_on=appeal.stage_started_on,
    )
    assert insurer_is_overdue(as_if_filed_at_notice, world.now(), None) is True
    assert (world.now() - as_if_filed_at_notice.theirs) == timedelta(days=90)


def test_the_sweep_of_the_whole_world_accuses_only_the_plan_that_was_actually_written_to():
    """Both appeals sit on the same plan and the same clock. One was posted in June
    and has been ignored for nineteen days past the sixty; the other was never sent.
    Only the first is reported as overdue."""
    world, case = seeded()
    overdue = {
        f.appeal.appeal_id: f.insurer_overdue for f in sweep(case, world.now())
    }
    assert overdue["appeal-16"] is True
    assert overdue["appeal-50"] is False
    assert case.appeals["appeal-16"].sent_on is not None

    late = next(f for f in sweep(case, world.now()) if f.appeal.appeal_id == "appeal-16")
    assert "19 days past its own deadline to answer" in late.sentence
