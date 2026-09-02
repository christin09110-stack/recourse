"""Resuming the run a person approved — and refusing to resume one they refused.

**A decline never reaches an agent.** The API enforces that in `routes_decisions` by
not calling this at all, and this module enforces it again by raising if it is called
anyway. Two locks on one door, on purpose. Muster had one — the SDK's `evaluate`
callback — and against the deployed service it did not hold: an operator declined a
change, the resumed run performed it, and the receipt carried the name of the person
who had refused it. A framework callback is not where that guarantee belongs.

Which loop to resume is read from the stopped call itself. The guarded tools of the
two loops are disjoint, so the tool the person was asked about says which agent asked.
Guessing would be worse than failing: resuming the wrong loop would answer a question
nobody had asked with a decision somebody had made about something else.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.types import DecisionOutcome
from recourse.hooks.audit import AuditTrail
from recourse.loops.press.tools import PRESS_TOOLS
from recourse.loops.watch.tools import WATCH_TOOLS


def loop_for(proposal: dict[str, Any]) -> str:
    """"watch" or "press", from the tool the run stopped on."""
    tool = str(proposal.get("tool", ""))
    if tool in WATCH_TOOLS:
        return "watch"
    if tool in PRESS_TOOLS:
        return "press"
    raise LookupError(
        f"the stopped call {tool!r} belongs to neither loop, so there is no run to "
        "resume. A decision parked without the tool it was about cannot be honoured."
    )


def _record(pending: Any) -> dict[str, Any]:
    """The structured answer the agent is resumed with, and the journal keeps."""
    decision = pending.decision
    return {"outcome": decision.outcome.value, "by": decision.by,
            "role": decision.role, "note": decision.note}


async def resume_decision(state: Any, pending: Any) -> Any:
    """Resume the paused run this decision belongs to. Approvals only.

    A fresh agent, deliberately: the previous instance is gone and its snapshot is
    what carries the conversation. That means a new tools closure with empty caches,
    which is why `press.board.Board` re-derives on a miss rather than refusing an
    appeal the previous instance had surfaced.
    """
    if pending.decision.outcome is not DecisionOutcome.APPROVE:
        raise ValueError(
            f"decision {pending.decision.decision_id!r} was "
            f"{pending.decision.outcome.value if pending.decision.outcome else 'unanswered'}, "
            "and a run is never resumed on anything but an approval. Resuming a "
            "decline performs the refused act and puts the refuser's name on it."
        )

    kind = loop_for(pending.proposal)
    trail: AuditTrail = state.trail
    if kind == "watch":
        from recourse.loops.watch import runner as watch

        policy = watch.build_default_policy(state.store, state.world.now, state.autonomy,
                                            prompted=True)
        agent = watch.build_watch_agent(state.store, state.world.now, policy, trail)
        return await watch.resume_watch(agent, pending.snapshot, pending.interrupt_id,
                                        _record(pending), policy)

    from recourse.loops.press import runner as press

    policy = press.build_default_policy(state.store, state.world.now, state.autonomy)
    agent = press.build_press_agent(state.store, state.world.now, policy, trail,
                                    state.autonomy)
    return await press.resume_press(agent, pending.snapshot, pending.interrupt_id,
                                    _record(pending), policy)
