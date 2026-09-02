"""The three PRESS tools that change something: the answer, the stage, and the word.

None of them files. There is no tool in this loop that submits an appeal to anyone —
`advance_stage` opens the *next* level's record and its clock, and a person still
sends the letter.

The dates and the stages are derived, never taken from the model. `record_response`
hands a missing date straight to the store and lets it raise, because the store's
refusal already says the thing worth saying: the next level's clock starts from that
date, and without it the countdown never begins and nothing complains.
"""

from __future__ import annotations

from typing import Any

from strands import tool

from recourse.domain.types import Outcome
from recourse.loops.press.answer import ANSWERS, read_date, read_outcome
from recourse.loops.press.board import Board
from recourse.loops.press.staging import arrived_at, what_changes
from recourse.persistence.store import CaseStore


def build_writing_tools(store: CaseStore, board: Board,
                        notices: list[dict[str, Any]]) -> list[Any]:
    @tool
    def record_response(appeal_id: str, outcome: str, answered_on: str = "") -> Any:
        """Record what the plan said, the date it said it, and what follows.

        `outcome` is one of overturned, partly_overturned or upheld. If it is upheld,
        the reply names the next stage and what actually changes there.
        """
        found = read_outcome(outcome)
        if found is None:
            return {"error": f"{outcome!r} is not an answer; use one of "
                             + ", ".join(o.value for o in ANSWERS)}
        try:
            # The date goes to the store even when it is missing, so the refusal
            # comes from the one place that knows why it matters rather than from a
            # paraphrase here that would drift from it.
            appeal = store.record_response(appeal_id, found, read_date(answered_on))
        except (KeyError, ValueError) as exc:
            return {"error": str(exc)}
        reply = {"appeal_id": appeal_id, "outcome": found.value,
                 "answered_on": appeal.answered_on.isoformat(), "stage": appeal.stage.value}
        if found is Outcome.OVERTURNED:
            return {**reply, "next_stage": None,
                    "what_changes": "The denial is reversed. There is nothing left to appeal."}
        return {**reply, **what_changes(board.clocks_on(appeal_id))}

    @tool
    def advance_stage(appeal_id: str) -> Any:
        """Open the next level of this appeal. Which level, and when, is computed.

        Neither the stage nor the start date is taken from the model: the stage comes
        from the plan's own rules and the date is when this level was answered.
        """
        try:
            appeal = store.appeal(appeal_id)
        except KeyError as exc:
            return {"error": str(exc)}
        if appeal.outcome is Outcome.OVERTURNED:
            return {"error": f"appeal {appeal_id!r} was overturned; there is nothing "
                             "left to contest and advancing it would file against a win"}
        clocks = board.clocks_on(appeal_id)
        if clocks is None or clocks.next_stage is None:
            return {"error": f"no next stage follows {appeal.stage.value} on this plan"}
        try:
            moved = store.advance_stage(appeal_id, clocks.next_stage, appeal.answered_on)
        except ValueError as exc:
            return {"error": str(exc)}
        return {"appeal_id": appeal_id,
                "started_on": moved.stage_started_on.isoformat(),
                **arrived_at(moved.stage, board.clocks_on(appeal_id))}

    @tool
    def notify_person(appeal_id: str, message: str) -> Any:
        """Tell the claimant something about this appeal, with the clock attached."""
        row = board.entry(appeal_id)
        if row is None:
            return {"error": f"no open appeal {appeal_id!r}; call sweep_deadlines first"}
        notice = {"appeal_id": appeal_id, "message": message,
                  # The computed sentence travels with the model's message so what the
                  # person reads about the clock is never the model's arithmetic.
                  "deadline": row["sentence"], "risk": row["risk"]}
        notices.append(notice)
        return {"notified": True, **notice}

    return [record_response, advance_stage, notify_person]
