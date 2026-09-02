# tests/adapters/test_seed_is_not_embarrassing.py
"""Scrutiny of the seed itself.

Muster's first demo rota was a labour-law violation and nobody noticed until it was
on screen. These are the equivalent failures here: an EOB whose columns do not add
up, dates out of order, a plan whose `internal_levels` disagrees with its own
rulebook, and an insurer reported overdue on an appeal that was never sent.
"""

from __future__ import annotations

from recourse.adapters.frozen import DAYS_SINCE_APPEAL_SENT, INSURER_OVERDUE_BY
from recourse.domain.clocks import insurer_is_overdue
from recourse.domain.money import Money
from recourse.domain.types import ServiceType
from recourse.rulebook.loader import for_plan_type

from tests.adapters.conftest import deadlines_of


def _lines(case):
    return [line for claim in case.claims.values() for line in claim.lines]


def test_every_lines_money_adds_up(case):
    for line in _lines(case):
        assert line.billed >= line.allowed >= Money.zero(), line.line_id
        assert line.plan_paid >= Money.zero() and line.patient_responsibility >= Money.zero()
        assert line.plan_paid + line.patient_responsibility == line.allowed, line.line_id


def test_no_service_is_dated_after_the_notice_that_refused_it(case, world):
    for claim in case.claims.values():
        assert claim.notice_date <= world.now(), claim.claim_id
        for line in claim.lines:
            assert line.service_date <= claim.notice_date, line.line_id


def test_no_document_arrives_from_the_future(case, world):
    for document in case.documents.values():
        assert document.received_on <= world.now(), document.document_id


def test_every_appeal_starts_on_its_own_claims_notice_date(case):
    """`stage_started_on` at level one *is* the notice date; a seed that drifted
    would put every downstream deadline a few days out with nothing to show for it."""
    for appeal in case.appeals.values():
        claim = case.claims[case.denials[appeal.denial_id].claim_id]
        assert appeal.stage_started_on == claim.notice_date, appeal.appeal_id
        if appeal.sent_on is not None:
            assert appeal.stage_started_on <= appeal.sent_on


def test_each_plans_internal_levels_agree_with_its_own_rulebook(case):
    for plan in case.plans.values():
        rules = for_plan_type(plan.plan_type)
        assert plan.internal_levels == rules.internal_levels, plan.plan_id
        # And the plan ships answer clocks for the number of levels it claims.
        rules.decision_on_appeal.for_levels(plan.internal_levels)


def test_the_overdue_offset_is_measured_against_the_rulebooks_own_figure(case):
    """The 60 days the seed subtracts from is the marketplace figure, read back
    from the rulebook rather than trusted — so moving the data moves the demo."""
    aca = next(p for p in case.plans.values() if p.plan_id == "plan-aca")
    table = for_plan_type(aca.plan_type).decision_on_appeal.for_levels(1)
    (figure,) = table.for_service(ServiceType.POST_SERVICE)
    assert figure.value == 60 and figure.unit == "days"
    assert DAYS_SINCE_APPEAL_SENT == figure.value + INSURER_OVERDUE_BY


def test_only_a_sent_appeal_is_presented_as_having_an_overdue_insurer(case, world):
    """The plan's clock runs from the day the appeal was posted. Counting it from
    the denial notice reported Harbor Blue as ninety days late answering
    `appeal-50`, which was never sent to them — a false accusation the deadline
    screen would have shown as fact. No `sent_on` gate is needed at the call site
    any more, because an unfiled appeal now has no `theirs` date at all."""
    overdue = [
        appeal.appeal_id for appeal in case.appeals.values()
        if insurer_is_overdue(deadlines_of(case, appeal), world.now(), appeal.answered_on)
    ]
    assert overdue == ["appeal-16"]

    unsent = case.appeals["appeal-50"]
    assert unsent.sent_on is None
    assert deadlines_of(case, unsent).theirs is None
