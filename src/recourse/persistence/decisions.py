"""What a paused run is waiting to be told, and what it is waiting with.

Separate from `inbox.py` so that the queue's rules and the shape of a question are
not read as one thing: `Decision` is the question and the answer, `PendingDecision`
is everything needed to resume the run that asked it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from recourse.domain.types import DecisionOutcome


@dataclass(frozen=True)
class Decision:
    """One question put to a person, and — once answered — who answered it."""

    decision_id: str
    rule: str
    prompt: str
    appeal_id: str = ""
    outcome: DecisionOutcome | None = None
    by: str = ""
    role: str = ""
    note: str = ""
    at: datetime | None = None

    def answer(self, outcome: DecisionOutcome, *, by: str, role: str, note: str = "") -> Decision:
        return Decision(
            decision_id=self.decision_id, rule=self.rule, prompt=self.prompt,
            appeal_id=self.appeal_id, outcome=outcome, by=by, role=role, note=note,
            at=datetime.now(timezone.utc),
        )


@dataclass
class PendingDecision:
    decision: Decision
    interrupt_id: str
    snapshot: dict[str, Any]
    rule_hits: list[dict[str, str]] = field(default_factory=list)
    #: The guarded call this run stopped on: which tool, and its arguments.
    proposal: dict[str, Any] = field(default_factory=dict)
    #: Rises while a deadline escalation goes unanswered. See `DecisionInbox.raise_severity`.
    severity: int = 1
