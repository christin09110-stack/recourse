"""What we intend to do about a denial, and the clocks it runs against.

One shape here is load-bearing. An `Assertion` is a sentence *plus the document it
came from*, and a clinical one without a `document_id` is not a weak assertion, it is
an invalid object. That is what lets `CitationGuard` be enforcement rather than an
instruction in a prompt: an appeal that invents a symptom is a false statement on an
insurance document, and the type system should make that awkward to build.

`Deadlines` distinguishes a clock that has not started from one that has run out. A
two-level ERISA appeal whose first level is unanswered genuinely has no second-level
date, and saying so is more use than a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from recourse.domain.types import AppealStage, Outcome


@dataclass(frozen=True)
class Assertion:
    """A sentence in an appeal, and the document behind it.

    `document_id` is optional only for sentences that are not clinical — a claim
    number, a date, the amount in dispute. `packet.build_letter_body` raises on a
    clinical assertion with nothing behind it rather than writing it.
    """

    text: str
    clinical: bool = False
    document_id: str | None = None


@dataclass(frozen=True)
class Appeal:
    appeal_id: str
    denial_id: str
    plan_id: str
    stage: AppealStage
    outcome: Outcome = Outcome.PENDING
    #: When this stage's clock started: the notice date for level one, and the date
    #: the previous level was answered for anything after it.
    stage_started_on: date | None = None
    #: Set when the insurer answers. Until then the next stage has no start date and
    #: `clocks` says so rather than inventing one.
    answered_on: date | None = None
    letter_body: str = ""
    assertions: tuple[Assertion, ...] = ()
    sent_on: date | None = None

    @property
    def is_open(self) -> bool:
        return self.outcome is Outcome.PENDING


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
