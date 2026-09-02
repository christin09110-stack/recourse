"""Where a paused run waits for a human.

When the escalation policy stops a run, the snapshot and interrupt id are parked
here alongside the question. A person answers; the orchestrator uses the stored
snapshot to resume the very same run.

In memory, deliberately: this build has no durable store, and pretending otherwise
would be worse than saying so. Restart the process and every pending decision, and
the snapshot needed to resume its run, is gone.

One thing here that Muster has no need for: `severity`. See `raise_severity`.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.types import DecisionOutcome
from recourse.persistence.decisions import Decision, PendingDecision


class DecisionInbox:
    def __init__(self) -> None:
        self._pending: dict[str, PendingDecision] = {}
        self._answered: list[PendingDecision] = []

    def open(
        self,
        decision: Decision,
        *,
        interrupt_id: str,
        snapshot: dict[str, Any],
        rule_hits: list[dict[str, str]],
        proposal: dict[str, Any] | None = None,
    ) -> str:
        """Park an escalation and return its id.

        `snapshot`, `rule_hits` and `proposal` are copied on the way in, so a caller
        that mutates its own dict afterwards cannot silently corrupt the parked
        state. Re-opening an id that is still pending raises: it would discard the
        earlier snapshot and interrupt id, which is exactly the failure this inbox
        exists to prevent.
        """
        if decision.decision_id in self._pending:
            raise KeyError(f"decision {decision.decision_id!r} is already pending")
        self._pending[decision.decision_id] = PendingDecision(
            decision=decision,
            interrupt_id=interrupt_id,
            snapshot=dict(snapshot),
            rule_hits=[dict(h) for h in rule_hits],
            proposal=dict(proposal or {}),
        )
        return decision.decision_id

    def pending(self) -> list[PendingDecision]:
        return list(self._pending.values())

    def answered(self) -> list[PendingDecision]:
        return list(self._answered)

    def get(self, decision_id: str) -> PendingDecision | None:
        return self._pending.get(decision_id)

    def answer(
        self, decision_id: str, outcome: DecisionOutcome, *, by: str, role: str, note: str = ""
    ) -> PendingDecision:
        if decision_id not in self._pending:
            raise KeyError(f"no pending decision {decision_id!r}")
        pending = self._pending.pop(decision_id)
        pending.decision = pending.decision.answer(outcome, by=by, role=role, note=note)
        self._answered.append(pending)
        return pending

    def raise_severity(self, decision_id: str) -> PendingDecision:
        """Make an unanswered escalation louder, and leave it open.

        This is a duty, not a nicety. `deadline_at_risk` fires *because* the agent
        must act: every other guard stops the agent doing something, and this one
        forces it to keep speaking. Silence is the failure mode of every background
        agent, and here it is the only unrecoverable one — a filing window that
        closes takes the merits of the appeal with it.

        So the escalation is never auto-dismissed, never expired and never quietly
        folded into the previous one. The number only moves up, until someone answers.
        """
        pending = self._pending.get(decision_id)
        if pending is None:
            raise KeyError(f"no pending decision {decision_id!r}")
        pending.severity += 1
        return pending
