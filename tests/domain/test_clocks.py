"""The arithmetic nobody else in this process is doing.

Every figure asserted here traces to a primary source: healthcare.gov for the ACA
marketplace clocks, 29 CFR 2560.503-1 for ERISA's, and 29 CFR 2590.715-2719 for the
external review that follows a non-grandfathered plan.
"""

from __future__ import annotations

from datetime import date

import pytest

from recourse.domain.clocks import (
    deadlines_for,
    insurer_is_overdue,
    risk_for,
)
from recourse.domain.models import Plan
from recourse.domain.types import (
    AppealStage,
    DeadlineRisk,
    PlanType,
    ServiceType,
)

NOTICE = date(2026, 6, 28)

ACA = Plan(plan_id="p-aca", name="Meridian Silver", plan_type=PlanType.ACA_MARKETPLACE,
           member_id="MB-1", internal_levels=1)
ERISA_TWO = Plan(plan_id="p-er2", name="Kestrel Group PPO",
                 plan_type=PlanType.ERISA_GROUP_HEALTH, member_id="MB-2",
                 internal_levels=2)
ERISA_ONE = Plan(plan_id="p-er1", name="Kestrel Group HMO",
                 plan_type=PlanType.ERISA_GROUP_HEALTH, member_id="MB-3",
                 internal_levels=1)
ERISA_GRANDFATHERED = Plan(plan_id="p-gf", name="Kestrel Legacy",
                           plan_type=PlanType.ERISA_GROUP_HEALTH, member_id="MB-4",
                           internal_levels=1, grandfathered=True)


def _first(plan, service=ServiceType.POST_SERVICE, started=NOTICE):
    return deadlines_for(plan=plan, service_type=service,
                         stage=AppealStage.INTERNAL_1, stage_started_on=started)


# -- the claimant's clock ----------------------------------------------------

def test_an_aca_denial_gives_180_days_to_appeal():
    """healthcare.gov: file the internal appeal within 180 days of the notice."""
    assert _first(ACA).mine == date(2026, 12, 25)


def test_erisa_also_gives_180_days_for_a_health_plan():
    """29 CFR 2560.503-1 (h)(3)(i). The two bodies of rules agree here; they
    diverge on what the plan owes back, not on what the claimant gets."""
    assert _first(ERISA_ONE).mine == _first(ACA).mine


# -- the insurer's clock -----------------------------------------------------

def test_a_one_level_post_service_appeal_must_be_answered_in_60_days():
    assert _first(ACA).theirs == NOTICE.replace(month=8, day=27)


def test_a_pre_service_appeal_must_be_answered_in_30():
    assert _first(ACA, ServiceType.PRE_SERVICE).theirs == date(2026, 7, 28)


def test_two_mandatory_erisa_levels_split_the_post_service_clock_into_30_and_30():
    """The difference that matters. A plan requiring two internal appeals owes 30
    days at each level rather than 60 once, so level one is answerable a month
    earlier than a reader of the headline figure would expect."""
    level_one = _first(ERISA_TWO)
    assert level_one.theirs == date(2026, 7, 28)
    assert level_one.next_stage is AppealStage.INTERNAL_2


def test_two_erisa_levels_split_pre_service_into_15_and_15():
    assert _first(ERISA_TWO, ServiceType.PRE_SERVICE).theirs == date(2026, 7, 13)


# -- a clock that has not started is not a clock that has run out ------------

def test_an_unanswered_first_level_leaves_the_second_with_no_dates_at_all():
    """The distinction the whole design rests on. Level two begins when level one
    is answered; until then there is no date, and inventing one would be worse
    than saying so."""
    second = deadlines_for(plan=ERISA_TWO, service_type=ServiceType.POST_SERVICE,
                           stage=AppealStage.INTERNAL_2, stage_started_on=None)
    assert second.mine is None
    assert second.theirs is None


def test_a_stage_that_has_not_started_is_not_at_risk():
    second = deadlines_for(plan=ERISA_TWO, service_type=ServiceType.POST_SERVICE,
                           stage=AppealStage.INTERNAL_2, stage_started_on=None)
    assert risk_for(second, date(2027, 1, 1), warn_days=30) is DeadlineRisk.OK


def test_the_second_level_dates_appear_once_the_first_is_answered():
    answered = date(2026, 8, 3)
    second = deadlines_for(plan=ERISA_TWO, service_type=ServiceType.POST_SERVICE,
                           stage=AppealStage.INTERNAL_2, stage_started_on=answered)
    assert second.theirs == date(2026, 9, 2)


# -- what follows ------------------------------------------------------------

def test_a_non_grandfathered_plan_goes_to_external_review():
    """29 CFR 2590.715-2719: four months to request it."""
    last = _first(ERISA_ONE)
    assert last.next_stage is AppealStage.EXTERNAL
    assert last.next_stage_window_days == 120


def test_a_grandfathered_plan_has_no_external_review_and_says_so():
    """2590.715-2719(a)(1)(ii) exempts them. Sending someone to a process that
    will not accept them is worse than telling them what is actually left."""
    assert _first(ERISA_GRANDFATHERED).next_stage is AppealStage.CIVIL_ACTION


def test_the_external_stage_carries_its_own_clocks():
    final_denial = date(2026, 9, 2)
    ext = deadlines_for(plan=ACA, service_type=ServiceType.POST_SERVICE,
                        stage=AppealStage.EXTERNAL, stage_started_on=final_denial)
    assert ext.mine == date(2026, 12, 31)
    assert ext.theirs == date(2026, 10, 17)
