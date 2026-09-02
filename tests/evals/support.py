"""The seeded household, and the two shorthands every scenario here shares.

Everything in this directory runs against `SimulatedWorld` — the same case file,
frozen clock, rulebook and X12 code table the product ships with. Nothing is stubbed
and no model is involved. A scenario that only holds against a fake says nothing
about what Recourse does when somebody's window is actually closing.

The dates below are the ones a scenario picks when it needs a denial of its own
rather than one of the seeded four. They are deliberately two weeks apart: the
claimant's clock runs from the day the refusal was posted and the plan's clock runs
from the day the appeal was posted, and a scenario that used one date for both would
pass while hiding the defect that used to live exactly there.
"""

from __future__ import annotations

from datetime import date

from recourse.adapters.simulated import SimulatedWorld
from recourse.domain.appeal import Deadlines
from recourse.domain.case import CaseFile
from recourse.domain.clocks import deadlines_for
from recourse.domain.models import Plan
from recourse.domain.types import AppealStage, ServiceType

#: The day the insurer posted the refusal.
NOTICE = date(2026, 3, 1)
#: The day a person actually put the appeal in the post, a fortnight later.
FILED = date(2026, 3, 15)


def seeded() -> tuple[SimulatedWorld, CaseFile]:
    """The Okafor–Reyes household on its frozen clock, and its live case file."""
    world = SimulatedWorld()
    return world, world.case_file()


def clocks(
    plan: Plan,
    *,
    stage: AppealStage = AppealStage.INTERNAL_1,
    started_on: date | None = NOTICE,
    filed_on: date | None = None,
    service_type: ServiceType = ServiceType.POST_SERVICE,
) -> Deadlines:
    """The real clock function, with the arguments a post-service denial carries.

    `filed_on` defaults to None because that is the ordinary state of an appeal: not
    yet sent. Nothing about the plan's clock has begun, and the scenarios rely on
    that being said rather than assumed.
    """
    return deadlines_for(
        plan=plan, service_type=service_type, stage=stage,
        stage_started_on=started_on, filed_on=filed_on,
    )
