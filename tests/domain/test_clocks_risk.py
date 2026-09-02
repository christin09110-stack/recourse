"""How close a clock is, and the one that runs against the insurer."""

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


# -- risk --------------------------------------------------------------------

def test_a_missed_deadline_is_missed_and_never_softens_to_a_warning():
    """The only unrecoverable state here. A screen that downgraded it would be
    lying about the one thing it exists to prevent."""
    d = _first(ACA)
    assert risk_for(d, date(2026, 12, 26), warn_days=30) is DeadlineRisk.MISSED
    assert risk_for(d, date(2027, 6, 1), warn_days=30) is DeadlineRisk.MISSED


@pytest.mark.parametrize("today,expected", [
    (date(2026, 7, 1), DeadlineRisk.OK),
    (date(2026, 12, 1), DeadlineRisk.APPROACHING),
    (date(2026, 12, 22), DeadlineRisk.CRITICAL),
    (date(2026, 12, 25), DeadlineRisk.CRITICAL),
])
def test_risk_rises_as_the_window_closes(today, expected):
    assert risk_for(_first(ACA), today, warn_days=30) is expected


def test_the_day_the_deadline_falls_is_still_inside_it():
    """Off by one here costs somebody their appeal."""
    assert risk_for(_first(ACA), date(2026, 12, 25), warn_days=30) is not DeadlineRisk.MISSED


# -- the clock running against the insurer -----------------------------------

def test_an_insurer_past_its_own_deadline_is_reported():
    """The one clock in this process that runs against the plan, and nobody but
    the claimant is counting it."""
    d = _first(ACA)
    assert insurer_is_overdue(d, date(2026, 9, 15), answered_on=None) is True


def test_an_insurer_that_answered_is_not_overdue():
    d = _first(ACA)
    assert insurer_is_overdue(d, date(2026, 9, 15), answered_on=date(2026, 8, 1)) is False


def test_an_insurer_inside_its_window_is_not_overdue():
    d = _first(ACA)
    assert insurer_is_overdue(d, date(2026, 8, 1), answered_on=None) is False
