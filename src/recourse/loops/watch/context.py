"""What the policy judges a WATCH call on, read from the case file.

The agent supplies which denial. Everything that carries consequence — the class, the
clock, how many days are left, whether the plan is already late — is computed from the
record by the same functions the tools used. An agent that mis-states a deadline in its
argument is still judged on the real one.

Returning `None` means "unassessable", which the policy turns into an escalation. It
never means "fine". An unreadable code, a plan with no clock table and a missing notice
date all land here, and none of them is "no action needed".
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from recourse.domain.clocks import insurer_is_overdue, risk_for
from recourse.domain.types import AutonomyLevel, DenialClass
from recourse.loops.lookup import deadlines_at_notice, deadlines_of, resolve_denial
from recourse.loops.watch.tools import WATCH_TOOLS
from recourse.persistence.store import CaseStore
from recourse.policy.escalation import GUARDED_TOOLS
from recourse.policy.rules import THRESHOLDS, ActionContext


def build_watch_context_provider(
    store: CaseStore,
    clock: Callable[[], date],
    level: AutonomyLevel,
    prompted: bool = False,
) -> Callable[[str, dict[str, Any]], ActionContext | None]:
    """`prompted` is whether a person asked for this draft. Default False, so a level
    that does not draft unprompted escalates rather than assuming it was invited."""
    warn_days = THRESHOLDS[level].warn_days

    def provide(tool_name: str, args: dict[str, Any]) -> ActionContext | None:
        if tool_name not in GUARDED_TOOLS:
            return None

        resolved, _ = resolve_denial(store.case, str(args.get("denial_id", "")))
        if resolved is None:
            return None
        if resolved.denial.denial_class is DenialClass.UNASSESSABLE:
            return ActionContext(tool=tool_name, assessable=False)

        clocks = (deadlines_of(store.case, resolved.appeal) if resolved.appeal
                  else deadlines_at_notice(resolved))
        if clocks is None:
            return None

        today = clock()
        answered = resolved.appeal.answered_on if resolved.appeal else None
        return ActionContext(
            tool=tool_name,
            # Deliberately empty. `CitationGuard` runs before this handler and denies
            # an uncited clinical sentence outright; filling this in would turn that
            # Deny into a Confirm, and there is nothing for a person to approve about
            # a statement the record does not support. Offering it would invite
            # someone mid-triage to wave through a false statement on an insurance
            # document made in a patient's name.
            uncited_clinical=(),
            # Nothing in this loop files. A guarded call that is not one of the five
            # is a capability nobody declared, so it is treated as one that would.
            would_file=tool_name not in WATCH_TOOLS,
            risk=risk_for(clocks, today, warn_days),
            days_remaining=(clocks.mine - today).days if clocks.mine else None,
            insurer_overdue=insurer_is_overdue(clocks, today, answered),
            reaches_a_third_party=tool_name == "request_document",
            unprompted_draft=tool_name == "draft_letter_body" and not prompted,
            assessable=True,
        )

    return provide
