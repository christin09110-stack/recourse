"""The clocks attached to an appeal, and a question raised about one.

`Deadlines` distinguishes a clock that has not started from one that has run out. A
two-level ERISA appeal whose first level is unanswered genuinely has no second-level
date, and saying so is more use than a guess that will move.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from recourse.domain.types import AppealStage


@dataclass(frozen=True)
class Deadlines:
    """Every clock attached to one appeal at one stage.

    `mine` is what the claimant must do and by when. `theirs` is what the plan owes
    and by when — an insurer past its own limit is itself a fact worth raising, and
    the reason both live on one object.

    A `None` means the clock has not started, which is different from a clock that
    has run out. A two-level ERISA appeal whose first level is unanswered genuinely
    has no second-level date yet, and saying so is more use than a guess.
    """

    stage: AppealStage
    mine: date | None
    theirs: date | None
    next_stage: AppealStage | None
    next_stage_window_days: int | None
    #: Prose for the console and the escalation, e.g. "180 days from the notice date".
    basis: str = ""
    citation: str = ""


@dataclass(frozen=True)
class Escalation:
    """A question the agent will not answer for itself."""

    rule: str
    detail: str
    appeal_id: str | None = None
    raised_at: datetime | None = None
    #: Rises the longer a deadline escalation goes unanswered. The one thing this
    #: system must never do is go quiet as a clock runs out.
    severity: int = 1
