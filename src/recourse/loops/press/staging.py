"""What follows an upheld appeal, and what actually changes there.

`clocks.deadlines_for(...).next_stage` decides which door is next; this module says
what is behind it, because "external" and "civil_action" are not different amounts of
the same thing. One is a free review by an independent body that binds the plan. The
other is a lawsuit. Telling somebody the wrong one sends them to a process that will
not accept them, or stops them using one that would.

The fork is the plan's, not the denial's. An ERISA plan with two mandatory internal
levels has a second internal appeal before anything outside it; a grandfathered plan
has no external review right at all.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.appeal import Deadlines
from recourse.domain.types import AppealStage

_WHAT_CHANGES: dict[AppealStage, str] = {
    AppealStage.INTERNAL_2: (
        "This plan requires a second mandatory internal appeal before anything "
        "outside it (29 CFR 2560.503-1(c)(2)). The plan reviews its own decision "
        "again, and the clock for that level starts on the date this one was answered."
    ),
    AppealStage.EXTERNAL: (
        "An independent review organisation decides next, not the plan, and its "
        "decision binds the plan. The window to request it runs from this final "
        "internal denial."
    ),
    AppealStage.CIVIL_ACTION: (
        "There is no external review on this plan, so what remains is a civil action "
        "under ERISA 502(a). That is a lawyer's question, not this agent's, and these "
        "clocks stop here."
    ),
}


def describes(stage: AppealStage) -> str:
    """What is different about being at this stage, in a sentence."""
    return _WHAT_CHANGES.get(stage, "")


def what_changes(clocks: Deadlines | None) -> dict[str, Any]:
    """The stage that follows these clocks, and what is different about it."""
    if clocks is None or clocks.next_stage is None:
        return {"next_stage": None, "what_changes": "", "request_within_days": None}
    return {
        "next_stage": clocks.next_stage.value,
        "what_changes": describes(clocks.next_stage),
        "request_within_days": clocks.next_stage_window_days,
    }


def arrived_at(stage: AppealStage, clocks: Deadlines | None) -> dict[str, Any]:
    """What a just-opened stage means, and what would follow it in turn.

    Reported from the clocks recomputed *after* the move. Describing the pre-move
    clocks read as "you are now at external review, and next is external review",
    which is the kind of sentence that makes somebody stop trusting the screen.
    """
    return {
        "stage": stage.value,
        "what_changes": describes(stage),
        "my_deadline": clocks.mine.isoformat() if clocks and clocks.mine else None,
        "then": clocks.next_stage.value if clocks and clocks.next_stage else None,
    }
