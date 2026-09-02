"""The same denial under both plan types.

One code, one notice date, one filing date, two households. Adaeze buys her cover on
the marketplace; Marcus is covered through his employer under a plan governed by
ERISA that requires two mandatory internal appeals. Everything about the refusal is
identical. What differs is what happens next, and by when — which is the whole
argument for the rulebook being data rather than a paragraph in a prompt.

Read the two rows against each other:

    filing window        180 days   |   180 days
    plan must answer by   60 days   |    30 days
    next door            external   |   a second internal appeal
    window for it       120 days    |   not yet applicable

The row that surprises is the first. Going in, the expectation was that the ERISA
claimant would get a different amount of time to appeal. They do not — the 180 days
is the same, and the entire divergence is on the other side: the plan owes them an
answer in half the time, and then there is one more door before anybody outside the
plan looks at it.
"""

from __future__ import annotations

from datetime import timedelta

from recourse.loops.press import staging
from recourse.domain.types import AppealStage
from tests.evals.support import FILED, NOTICE, clocks, seeded


def test_both_claimants_get_the_same_hundred_and_eighty_days_to_appeal():
    """Not a coincidence of the seed: both rulebooks cite the same regulation for
    the same figure, one as the marketplace rule and one as 29 CFR 2560.503-1(h)(3)(i)."""
    _, case = seeded()
    marketplace = clocks(case.plans["plan-aca"], filed_on=FILED)
    employer = clocks(case.plans["plan-erisa"], filed_on=FILED)

    assert marketplace.mine == NOTICE + timedelta(days=180)
    assert employer.mine == marketplace.mine
    assert "govinfo.gov" in employer.citation


def test_the_employer_plan_owes_an_answer_in_half_the_time():
    """Because it splits a 60-day post-service answer across two mandatory levels:
    30 days at the first, and 30 more at the second once the first is answered."""
    _, case = seeded()
    marketplace = clocks(case.plans["plan-aca"], filed_on=FILED)
    employer = clocks(case.plans["plan-erisa"], filed_on=FILED)

    assert marketplace.theirs == FILED + timedelta(days=60)
    assert employer.theirs == FILED + timedelta(days=30)
    assert "60 days for the plan to answer" in marketplace.basis
    assert "30 days for the plan to answer" in employer.basis


def test_a_refusal_at_the_first_level_sends_them_to_two_different_places():
    """The marketplace claimant goes straight to an independent reviewer whose
    decision binds the plan. The employer-plan claimant has another internal appeal
    first — the plan reviewing its own decision again — and only then anything
    outside it."""
    _, case = seeded()
    marketplace = clocks(case.plans["plan-aca"], filed_on=FILED)
    employer = clocks(case.plans["plan-erisa"], filed_on=FILED)

    assert marketplace.next_stage is AppealStage.EXTERNAL
    assert employer.next_stage is AppealStage.INTERNAL_2

    assert "independent review organisation" in staging.describes(marketplace.next_stage)
    assert "second mandatory internal appeal" in staging.describes(employer.next_stage)


def test_only_one_of_them_has_a_countdown_to_the_next_stage_yet():
    """The marketplace claimant can be told the window now: four months from a final
    internal denial. The employer-plan claimant cannot, because the stage after
    theirs is another appeal to the same plan and its clock has not started.

    The 120 days is four months read as thirty-day months. It is two days short of
    four calendar months from this notice date — short in the safe direction, which
    is the only direction a rounding rule here is allowed to be wrong in.
    """
    _, case = seeded()
    marketplace = clocks(case.plans["plan-aca"], filed_on=FILED)
    employer = clocks(case.plans["plan-erisa"], filed_on=FILED)

    assert marketplace.next_stage_window_days == 120
    assert employer.next_stage_window_days is None
