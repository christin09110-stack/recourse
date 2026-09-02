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

from recourse.domain.deadline import Deadlines, Escalation  # noqa: F401  (re-export)
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
class StageRecord:
    """One level of one appeal, and everything that happened at it."""

    stage: AppealStage
    #: When this level's clock began: the notice date for the first, and the date
    #: the previous level was answered for anything after it.
    started_on: date | None = None
    letter_body: str = ""
    assertions: tuple[Assertion, ...] = ()
    sent_on: date | None = None
    answered_on: date | None = None
    outcome: Outcome = Outcome.PENDING

    @property
    def is_open(self) -> bool:
        return self.outcome is Outcome.PENDING


@dataclass(frozen=True)
class Appeal:
    """An appeal, as the stack of levels it has passed through.

    Not as "a stage plus some fields", which is how this started and was wrong. An
    ERISA plan may require two mandatory internal levels, and level two exists
    precisely to contest what level one decided — so a shape that overwrote the
    first level's outcome, date and letter on advancing destroyed the record the
    second level argues against.

    Advancing is an append. History is therefore intrinsic to the appeal rather than
    an artefact kept beside it by whatever mutated it, which also means the API can
    serialise an appeal and have its history come with it, and that a field added
    here later cannot silently survive a stage change by being forgotten in a list
    of things to blank.
    """

    appeal_id: str
    denial_id: str
    plan_id: str
    levels: tuple[StageRecord, ...]

    @classmethod
    def opened(
        cls, *, appeal_id: str, denial_id: str, plan_id: str,
        stage: AppealStage = AppealStage.INTERNAL_1,
        started_on: date | None = None, **level: object,
    ) -> Appeal:
        """A new appeal at its first level. The common case, said plainly."""
        return cls(appeal_id, denial_id, plan_id,
                   (StageRecord(stage=stage, started_on=started_on, **level),))

    @property
    def current(self) -> StageRecord:
        return self.levels[-1]

    @property
    def stage(self) -> AppealStage:
        return self.current.stage

    @property
    def outcome(self) -> Outcome:
        return self.current.outcome

    @property
    def stage_started_on(self) -> date | None:
        return self.current.started_on

    @property
    def answered_on(self) -> date | None:
        return self.current.answered_on

    @property
    def letter_body(self) -> str:
        return self.current.letter_body

    @property
    def assertions(self) -> tuple[Assertion, ...]:
        return self.current.assertions

    @property
    def sent_on(self) -> date | None:
        return self.current.sent_on

    @property
    def is_open(self) -> bool:
        return self.current.is_open

    @property
    def history(self) -> tuple[StageRecord, ...]:
        """The levels already answered, oldest first."""
        return self.levels[:-1]
