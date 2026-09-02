"""The two PRESS tools that only look: what is open, and what is running out.

`sweep_deadlines` is the whole loop in one call. It wraps `policy.sweep.sweep`, which
is pure and shared with the API and the tests, so the list the model reasons over is
the identical list the deadline screen shows — no second implementation to drift.

It returns findings worst first. A screen or a prompt that buried a missed window
under three warnings would be sorting by tidiness rather than by consequence, and the
whole point of this loop is that somebody hears about the clock in time.
"""

from __future__ import annotations

from typing import Any

from strands import tool

from recourse.loops.lookup import deadlines_of
from recourse.loops.press.board import Board, as_row
from recourse.persistence.store import CaseStore


def build_reading_tools(store: CaseStore, board: Board) -> list[Any]:
    @tool
    def open_appeals() -> Any:
        """Every appeal still awaiting an answer, with its stage and its clocks."""
        case = store.case
        rows: list[dict[str, Any]] = []
        for appeal in case.appeals.values():
            if not appeal.is_open:
                continue
            clocks = deadlines_of(case, appeal)
            rows.append({
                "appeal_id": appeal.appeal_id,
                "denial_id": appeal.denial_id,
                "plan_id": appeal.plan_id,
                "stage": appeal.stage.value,
                "outcome": appeal.outcome.value,
                "sent_on": appeal.sent_on.isoformat() if appeal.sent_on else None,
                "my_deadline": clocks.mine.isoformat() if clocks and clocks.mine else None,
                "their_deadline": (clocks.theirs.isoformat()
                                   if clocks and clocks.theirs else None),
                # None, not a guess. A plan type with no clock table is refused rather
                # than defaulted, and the caller escalates it as unassessable.
                "clocks_known": clocks is not None,
            })
        return rows

    @tool
    def sweep_deadlines() -> Any:
        """Every open appeal whose clock needs saying out loud, worst first.

        Includes appeals where the *plan* is past its own deadline to answer. That is
        the one clock in this process running against the insurer, and nobody but the
        claimant is counting it.
        """
        return [as_row(finding) for finding in board.sweep()]

    return [open_appeals, sweep_deadlines]
