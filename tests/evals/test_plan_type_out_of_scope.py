"""A plan type with no clock table.

Somebody's long-term disability claim is refused and they ask this system when they
have to appeal by. The right answer is "I do not know", and the wrong answer is 180
days — because a non-health ERISA plan gives 60 (29 CFR 2560.503-1(h)(2)(i)), and an
over-estimate here is the one error in this domain that cannot be undone. A person
told they have until October when they had until June does not get a worse appeal.
They get no appeal.

So the refusal is checked for the *number* as well as for happening at all.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from recourse.rulebook.loader import (
    PlanTypeNotInScope,
    available_plan_types,
    for_plan_type,
)
from recourse.domain.types import PlanType
from tests.evals.support import clocks, seeded


def test_asking_for_a_disability_plans_rules_is_refused_and_the_refusal_says_sixty_days():
    """The message names the figure the claimant actually has, not just the fact of
    a refusal. A stop that says 'unsupported' sends somebody looking elsewhere with
    nothing; this one hands them the number."""
    with pytest.raises(PlanTypeNotInScope) as refused:
        for_plan_type(PlanType.ERISA_NON_HEALTH)
    message = str(refused.value)
    assert "60 days" in message
    assert "180 days a health plan allows" in message
    assert "govinfo.gov" in message


def test_no_deadline_comes_back_at_all_rather_than_the_health_figure():
    """The refusal is not confined to the loader. Every clock in the system is
    computed through it, so asking for a date on such a plan raises rather than
    quietly producing one that is four months too generous."""
    _, case = seeded()
    disability = replace(
        case.plans["plan-erisa"], plan_id="plan-ltd",
        plan_type=PlanType.ERISA_NON_HEALTH, internal_levels=1,
    )
    with pytest.raises(PlanTypeNotInScope):
        clocks(disability)


def test_the_plan_type_is_absent_from_the_list_of_things_this_build_can_answer():
    """It is not offered and then refused. It is never offered."""
    assert PlanType.ERISA_NON_HEALTH not in available_plan_types()
    assert available_plan_types() == (
        PlanType.ACA_MARKETPLACE, PlanType.ERISA_GROUP_HEALTH,
    )
