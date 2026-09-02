"""An appeal whose first level was never answered.

Marcus's MRI denial sits on the employer plan, which requires two mandatory internal
appeals before anything outside it. Level two is a real stage with a real clock — and
that clock starts on the day level one is answered, not before. Meridian has not
answered. So there is no second-level date, and the interesting question is whether
the system says so or fills the gap in.

Filling it in would be worse than useless: a person shown a date computed from
nothing would plan around it, and it would move the moment the plan replied.
"""

from __future__ import annotations

from recourse.domain.clocks import next_stage_starts
from recourse.domain.types import AppealStage, Outcome
from tests.evals.support import clocks, seeded
from tests.loops.support import press


def test_the_second_level_has_no_dates_at_all_while_the_first_is_outstanding():
    """Both clocks come back empty — the claimant's and the plan's. Not a far-off
    date, not today's date: nothing."""
    _, case = seeded()
    plan = case.plans["plan-erisa"]
    assert plan.internal_levels == 2

    second = clocks(plan, stage=AppealStage.INTERNAL_2, started_on=None)
    assert second.mine is None
    assert second.theirs is None
    # What it will be, when it starts, is still known and still said.
    assert second.basis == "180 days to appeal; 30 days for the plan to answer"


def test_the_appeal_itself_reports_no_start_date_for_the_stage_above_it():
    """`next_stage_starts` is the date level two would begin from, and it is read off
    the answer that has not arrived."""
    _, case = seeded()
    appeal = case.appeals["appeal-197"]
    assert appeal.stage is AppealStage.INTERNAL_1
    assert appeal.outcome is Outcome.PENDING
    assert next_stage_starts(appeal) is None


def test_asking_the_agent_to_move_it_up_a_level_is_refused_in_plain_words():
    """The PRESS tool, driven for real. It does not advance and then compute; it
    declines, and the message says what advancing would have cost — a deadline
    invented rather than computed."""
    store, tools, _ = press()
    result = tools["advance_stage"](appeal_id="appeal-197")

    assert "error" in result
    assert "unanswered at internal_1" in result["error"]
    assert "would invent a deadline rather than compute one" in result["error"]
    assert store.appeal("appeal-197").stage is AppealStage.INTERNAL_1
    assert len(store.appeal("appeal-197").levels) == 1
