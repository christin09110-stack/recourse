"""The transitions of one appeal, as pure functions over a frozen object.

They live apart from `CaseStore` because the guards *are* the substance. What makes
a transition refusable has nothing to do with where the appeal is kept.

Advancing appends a level rather than overwriting one. Level two of an ERISA appeal
exists to contest what level one decided, so a shape that blanked level one's
outcome, date and letter on the way past destroyed the record level two argues
against — and did it by listing fields to clear, so a field added later would have
survived by being forgotten.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from recourse.domain.appeal import Appeal, StageRecord
from recourse.domain.types import AppealStage, Outcome


def _with_current(appeal: Appeal, updated: StageRecord) -> Appeal:
    return replace(appeal, levels=appeal.levels[:-1] + (updated,))


def responded(appeal: Appeal, outcome: Outcome, answered_on: date | None) -> Appeal:
    """Record the plan's answer to the level this appeal is at.

    `answered_on` is required, and not out of tidiness. The next stage's clock starts
    on the date this one was answered (29 CFR 2560.503-1 (i)(2)). An appeal marked
    upheld with no date leaves the level above it permanently unable to compute a
    deadline: `deadlines_for` reads the missing date as "this stage has not begun"
    and returns `None` forever, so the countdown that is the entire product never
    starts and nothing complains.
    """
    if answered_on is None:
        raise ValueError(
            f"appeal {appeal.appeal_id!r}: an answer needs the date it arrived. "
            "The next stage's clock starts from that date; without it the following "
            "level can never compute a deadline and the countdown never begins."
        )
    if outcome is Outcome.PENDING:
        raise ValueError(f"appeal {appeal.appeal_id!r}: 'pending' is not an answer")
    return _with_current(appeal, replace(appeal.current, outcome=outcome,
                                         answered_on=answered_on))


def advanced(appeal: Appeal, to_stage: AppealStage, started_on: date) -> Appeal:
    """Open the next level. Refused while this one is unanswered.

    The next level's clock begins when this one is answered, so advancing early would
    stamp a start date on a clock that has not started - a deadline invented out of
    nothing and shown to somebody as the day they must act by.
    """
    if appeal.answered_on is None:
        raise ValueError(
            f"appeal {appeal.appeal_id!r} is unanswered at {appeal.stage.value}: "
            f"{to_stage.value}'s clock starts when this level is answered, so "
            "advancing now would invent a deadline rather than compute one."
        )
    if to_stage is appeal.stage:
        raise ValueError(f"appeal {appeal.appeal_id!r} is already at {to_stage.value}")
    return replace(appeal, levels=appeal.levels + (
        StageRecord(stage=to_stage, started_on=started_on),
    ))


def lettered(appeal: Appeal, body: str, assertions: tuple) -> Appeal:
    """Attach a drafted letter to the level currently open."""
    return _with_current(appeal, replace(appeal.current, letter_body=body,
                                         assertions=tuple(assertions)))


def sent(appeal: Appeal, on: date) -> Appeal:
    """Record that a person sent it. Nothing in this system sends anything."""
    if not appeal.current.letter_body:
        raise ValueError(f"appeal {appeal.appeal_id!r} has no letter to send")
    return _with_current(appeal, replace(appeal.current, sent_on=on))
