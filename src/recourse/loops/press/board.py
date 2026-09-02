"""The per-run view of every open appeal, and the cache the PRESS tools read.

`sweep_deadlines` fills this; `advance_stage` and `notify_person` read it, so an
appeal_id they act on is one the sweep actually surfaced rather than one the model
composed.

**`entry` re-derives on a miss, and that is the whole reason this class exists.** A
resumed run is a *new* agent with a *new* tools closure, so the cache is empty even
though the person has just approved acting on an appeal the previous instance
surfaced. Muster hit exactly this: an approved option was refused as unknown, the
model tried a different worker, that escalated too, and approving a decision produced
a fresh copy of the same question. Re-deriving costs one sweep and keeps the
guarantee intact — the appeal must still be one `sweep` produces, so an id the model
invented is still refused.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from recourse.domain.types import AutonomyLevel
from recourse.loops.lookup import deadlines_of
from recourse.persistence.store import CaseStore
from recourse.policy.finding import Finding
from recourse.policy.sweep import sweep


def as_row(finding: Finding) -> dict[str, Any]:
    """One finding, in the shape both the tools and the console read."""
    clocks = finding.deadlines
    return {
        "appeal_id": finding.appeal.appeal_id,
        "denial_id": finding.appeal.denial_id,
        "stage": finding.appeal.stage.value,
        "outcome": finding.appeal.outcome.value,
        "risk": finding.risk.value,
        "days_remaining": finding.days_remaining,
        "insurer_overdue": finding.insurer_overdue,
        "my_deadline": clocks.mine.isoformat() if clocks.mine else None,
        "their_deadline": clocks.theirs.isoformat() if clocks.theirs else None,
        "next_stage": clocks.next_stage.value if clocks.next_stage else None,
        "sentence": finding.sentence,
    }


class Board:
    """One run's picture of the open appeals. Build one per run, never share."""

    def __init__(self, store: CaseStore, clock: Callable[[], date],
                 level: AutonomyLevel) -> None:
        self._store = store
        self._clock = clock
        self._level = level
        self._rows: dict[str, dict[str, Any]] = {}

    def sweep(self) -> tuple[Finding, ...]:
        """Every open appeal that needs saying out loud, worst first, and cache it."""
        findings = sweep(self._store.case, self._clock(), self._level)
        self._rows = {f.appeal.appeal_id: as_row(f) for f in findings}
        return findings

    def entry(self, appeal_id: str) -> dict[str, Any] | None:
        """One appeal's row, re-deriving the cache on a miss. See the module docstring."""
        if appeal_id not in self._rows:
            self.sweep()
        return self._rows.get(appeal_id)

    def clocks_on(self, appeal_id: str) -> Any:
        """The live clocks for one appeal, straight from the record.

        Read fresh rather than off the cached row: `record_response` moves an appeal
        underneath the cache, and the next stage is computed from where it is *now*.
        """
        return deadlines_of(self._store.case, self._store.appeal(appeal_id))
