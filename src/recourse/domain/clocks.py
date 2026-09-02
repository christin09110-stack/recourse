"""Every deadline, as arithmetic.

No language model computes a date anywhere in this system. A model that miscounts a
deadline by a fortnight does not produce a slightly worse answer; it produces a
missed 180-day window, and the merits of an appeal filed late stop mattering. So the
clocks are pure functions over a notice date, a plan's rules and a stage, and the
agent is only ever allowed to call them.

Two distinctions in here carry the design.

**A clock that has not started is not a clock that has run out.** An ERISA plan may
require two mandatory internal appeals, and the second level's clock begins when the
first is *answered*. Until then there is genuinely no second-level date, and
`Deadlines.mine` is `None` rather than a guess. Saying "not yet" is more use to
somebody than a date that will move.

**`MISSED` is terminal.** It never softens back to `APPROACHING` on a later sweep. A
screen that downgraded a missed filing window to a warning would be lying about the
only unrecoverable state in this domain.
"""

from __future__ import annotations

from datetime import date, timedelta

from recourse.domain.appeal import Appeal, Deadlines
from recourse.domain.models import Plan
from recourse.domain.types import AppealStage, DeadlineRisk, ServiceType
from recourse.domain.units import days as _days
from recourse.domain.units import internal_stage_index as _internal_stage_index
from recourse.rulebook.loader import for_plan_type

def _next_after_internal(plan: Plan, stage: AppealStage) -> AppealStage | None:
    """What follows this internal level for this particular plan."""
    rules = for_plan_type(plan.plan_type)
    if _internal_stage_index(stage) + 1 < plan.internal_levels:
        return AppealStage.INTERNAL_2
    if rules.external_review and not plan.grandfathered:
        return AppealStage.EXTERNAL
    # A grandfathered plan has no external review right; what is left is a civil
    # action under ERISA 502(a), and calling that "external review" would send
    # somebody to a process that will not accept them.
    return AppealStage.CIVIL_ACTION


def deadlines_for(
    *,
    plan: Plan,
    service_type: ServiceType,
    stage: AppealStage,
    stage_started_on: date | None,
    filed_on: date | None = None,
) -> Deadlines:
    """The clocks attached to one appeal at one stage.

    `stage_started_on` is the notice date for a first-level appeal, and the date the
    previous level was answered for anything after it. `None` means this stage has
    not begun, and every date comes back `None` rather than invented.

    `filed_on` is when the appeal was actually posted, and it is what the *plan's*
    deadline runs from — not the notice date. Getting that wrong reported an insurer
    as three months late answering an appeal nobody had sent them yet, which is a
    false accusation the console would have shown as fact.
    """
    rules = for_plan_type(plan.plan_type)

    if stage in (AppealStage.INTERNAL_1, AppealStage.INTERNAL_2):
        return _internal(rules, plan, service_type, stage, stage_started_on, filed_on)
    if stage is AppealStage.EXTERNAL:
        return _external(rules, stage_started_on)
    return Deadlines(
        stage=stage, mine=None, theirs=None, next_stage=None,
        next_stage_window_days=None,
        basis="a civil action under ERISA 502(a) is not governed by these clocks",
    )


def _internal(rules, plan, service_type, stage, started_on, filed_on) -> Deadlines:
    to_appeal = _days(rules.time_to_appeal)
    decision = rules.decision_on_appeal.for_levels(plan.internal_levels)
    theirs_figure = decision.for_service(service_type)[_internal_stage_index(stage)]
    nxt = _next_after_internal(plan, stage)
    window = None
    if nxt is AppealStage.EXTERNAL and rules.external_review:
        window = _days(rules.external_review.request_within)

    return Deadlines(
        stage=stage,
        mine=started_on + timedelta(days=to_appeal) if started_on else None,
        theirs=filed_on + timedelta(days=_days(theirs_figure)) if filed_on else None,
        next_stage=nxt,
        next_stage_window_days=window,
        basis=f"{to_appeal} days to appeal; {_days(theirs_figure)} days for the plan to answer",
        citation=rules.time_to_appeal.citation,
    )


def _external(rules, started_on) -> Deadlines:
    review = rules.external_review
    if review is None:
        return Deadlines(
            stage=AppealStage.EXTERNAL, mine=None, theirs=None,
            next_stage=AppealStage.CIVIL_ACTION, next_stage_window_days=None,
            basis="this plan ships no external review clocks",
        )
    request = _days(review.request_within)
    return Deadlines(
        stage=AppealStage.EXTERNAL,
        mine=started_on + timedelta(days=request) if started_on else None,
        theirs=(started_on + timedelta(days=_days(review.standard_decision))
                if started_on else None),
        next_stage=AppealStage.CIVIL_ACTION,
        next_stage_window_days=None,
        basis=f"{request} days to request review; "
              f"{_days(review.standard_decision)} days for a decision",
        citation=review.request_within.citation,
    )


def risk_for(deadlines: Deadlines, now: date, warn_days: int) -> DeadlineRisk:
    """How close the claimant's own clock is to running out.

    A stage that has not started is `OK` — there is nothing to be late for yet.
    """
    if deadlines.mine is None:
        return DeadlineRisk.OK
    remaining = (deadlines.mine - now).days
    if remaining < 0:
        return DeadlineRisk.MISSED
    if remaining <= max(1, warn_days // 5):
        return DeadlineRisk.CRITICAL
    if remaining <= warn_days:
        return DeadlineRisk.APPROACHING
    return DeadlineRisk.OK


def insurer_is_overdue(deadlines: Deadlines, now: date, answered_on: date | None) -> bool:
    """Whether the plan has blown its own deadline to answer.

    Worth surfacing on its own. It is the one clock in this process that runs
    against the insurer, and nobody but the claimant is counting it.
    """
    # `theirs` is None until the appeal is actually filed, which is the guard that
    # matters: an unsent appeal has not started anybody's clock, and saying the plan
    # is late answering it would be an accusation about a letter they never received.
    if deadlines.theirs is None or answered_on is not None:
        return False
    return now > deadlines.theirs


def next_stage_starts(appeal: Appeal) -> date | None:
    """When the following stage's clock begins: the date this one was answered.

    `None` while the current level is outstanding, which is the honest answer and
    the reason a two-level ERISA appeal shows no second-level date until the first
    comes back.
    """
    return appeal.answered_on
