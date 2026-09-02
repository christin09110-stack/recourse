"""What the policy judges a PRESS call on, read from the case file.

The agent supplies which appeal. The stage, the clocks, how many days remain and
whether the plan is already late are all computed from the record, so an agent that
mis-states a deadline in its argument is still judged on the real one.

`None` means "unassessable", which escalates. It never means "fine".

One asymmetry worth naming. `notify_person` is guarded, and the deadline rules fire
on it — but they fire *for* it. `deadline_at_risk` is a duty rather than a
prohibition: it is the rule that exists to make the agent speak, and a run that pauses
on it is a run asking a person to look at a closing window, which is the product.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from recourse.domain.clocks import insurer_is_overdue, risk_for
from recourse.domain.types import AutonomyLevel
from recourse.loops.lookup import deadlines_of
from recourse.loops.press.tools import PRESS_TOOLS
from recourse.persistence.store import CaseStore
from recourse.policy.escalation import GUARDED_TOOLS
from recourse.policy.rules import THRESHOLDS, ActionContext


def build_press_context_provider(
    store: CaseStore,
    clock: Callable[[], date],
    level: AutonomyLevel,
) -> Callable[[str, dict[str, Any]], ActionContext | None]:
    warn_days = THRESHOLDS[level].warn_days

    def provide(tool_name: str, args: dict[str, Any]) -> ActionContext | None:
        if tool_name not in GUARDED_TOOLS:
            return None

        appeal_id = str(args.get("appeal_id", ""))
        appeal = store.case.appeals.get(appeal_id)
        if appeal is None:
            return None
        clocks = deadlines_of(store.case, appeal)
        if clocks is None:
            return None

        today = clock()
        return ActionContext(
            tool=tool_name,
            # `CitationGuard` runs first and denies an uncited clinical sentence
            # outright. Filling this in would turn that Deny into a Confirm, and a
            # statement the record does not support is not something to offer for
            # approval. Nothing in this loop writes an assertion in any case.
            uncited_clinical=(),
            # Nothing here files. A guarded call that is not one of the five is a
            # capability nobody declared, so it is treated as one that would.
            would_file=tool_name not in PRESS_TOOLS,
            risk=risk_for(clocks, today, warn_days),
            days_remaining=(clocks.mine - today).days if clocks.mine else None,
            insurer_overdue=insurer_is_overdue(clocks, today, appeal.answered_on),
            # Telling the claimant is not reaching a third party. This loop asks
            # nobody outside the household for anything.
            reaches_a_third_party=False,
            unprompted_draft=False,
            assessable=True,
        )

    return provide
