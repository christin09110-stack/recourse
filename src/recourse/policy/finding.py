"""One appeal, and why it needs saying out loud.

The sentence lives here rather than in the console because it is what a person is
actually told, and it should read the same in a notification, an escalation and a
screen. Never a rule code: somebody being told their appeal window is closing should
not have to look anything up.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from recourse.domain.appeal import Appeal, Deadlines
from recourse.domain.types import DeadlineRisk


@dataclass(frozen=True)
class Finding:
    """One appeal, and why it needs saying out loud."""

    appeal: Appeal
    deadlines: Deadlines
    risk: DeadlineRisk
    days_remaining: int | None
    insurer_overdue: bool

    @property
    def needs_raising(self) -> bool:
        return self.risk is not DeadlineRisk.OK or self.insurer_overdue

    @property
    def sentence(self) -> str:
        """What a person is actually told. Plain, and never a rule code."""
        if self.risk is DeadlineRisk.MISSED:
            return ("The window to appeal this has closed. Nothing about the merits "
                    "matters now.")
        parts: list[str] = []
        if self.days_remaining is not None and self.risk is not DeadlineRisk.OK:
            parts.append(f"{self.days_remaining} days left to appeal this.")
        if self.insurer_overdue and self.deadlines.theirs:
            over = (self._today - self.deadlines.theirs).days if self._today else None
            parts.append(
                f"The plan is {over} days past its own deadline to answer."
                if over is not None else
                "The plan is past its own deadline to answer."
            )
        return " ".join(parts) or "This is on track."

    #: Set by `sweep`, so `sentence` can say how far past the plan is.
    _today: date | None = None
