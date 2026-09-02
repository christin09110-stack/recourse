"""The Okafor–Reyes household: the seeded demo world, on a frozen clock.

One family, one hospital episode and some outpatient care, across two plans — a
marketplace policy with a single internal appeal and an employer plan governed by
ERISA that requires two. Four denials among nine claim lines, which is roughly the
rate a real household meets, and three of those four are the demo:

* **CARC 16**, clerical. The EOB alone supports the appeal, so Recourse drafts it.
* **CARC 197**, authorisation — and the approval letter has been in the file since
  five weeks before the scan. Nothing is missing; it was simply never attached.
* **CARC 50**, clinical. There is no clinician letter, and there is not supposed to
  be: this is the one the agent hands back.

The clock is frozen at 2026-09-02 and every date in the world is an offset from it,
so a countdown in a recording is reproducible. Two of those offsets are load-bearing
and are asserted in `tests/adapters/`, not merely intended: one appeal sits at day
150 of its 180, and one insurer is 19 days past its own 60.

**Why the seed is checked as strictly as the product.** Muster's first seeded week
was itself a labour-law violation — a compliance demo arguing against itself — and
nobody noticed until it was on screen. The equivalent failures here are an EOB whose
columns do not add up, a denial whose class contradicts its own code, a plan whose
`internal_levels` disagrees with its rulebook, and a document that arrives before the
service it describes. Every one of those has a test, because the seed is the first
thing a viewer reads and the last thing anyone reviews.
"""

from __future__ import annotations

from datetime import date, datetime

from recourse.adapters import seed_appeals, seed_claims, seed_plans
from recourse.adapters.frozen import FROZEN_NOW, FROZEN_TODAY
from recourse.domain.case import CaseFile
from recourse.domain.models import Plan

CASE_ID = "case-okafor-reyes"


def build_case_file() -> CaseFile:
    """Assemble the seeded case file. Pure: the same call gives the same world."""
    claims = seed_claims.claims()
    return CaseFile(
        case_id=CASE_ID,
        plans=seed_plans.plans(),
        claims=claims,
        documents=seed_plans.documents(),
        denials=seed_appeals.denials(claims),
        appeals=seed_appeals.appeals(),
    )


class SimulatedWorld:
    """The demo world: a frozen clock and one household's case file."""

    def __init__(self, today: date | None = None) -> None:
        #: Overridable so a test can wind the clock on without rebuilding the seed.
        self._today = today if today is not None else FROZEN_TODAY
        self._case = build_case_file()

    def now(self) -> date:
        """The frozen today. Every deadline in the console is measured from this."""
        return self._today

    def now_at(self) -> datetime:
        """The same instant, for anything stamping a timestamp rather than a date."""
        if self._today == FROZEN_TODAY:
            return FROZEN_NOW
        return datetime.combine(self._today, FROZEN_NOW.timetz())

    def case_file(self) -> CaseFile:
        """The live case file — the same object, so a document added stays added."""
        return self._case

    def plan_for(self, plan_id: str) -> Plan | None:
        return self._case.plans.get(plan_id)

    def reset(self) -> None:
        """Rebuild the world from the seed, for `POST /api/demo/reset`."""
        self._case = build_case_file()
