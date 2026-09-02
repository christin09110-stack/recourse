"""Reading what the model said the plan said.

Both functions hand back `None` rather than a fallback, and the difference matters
more for the date than for the outcome. An unparseable date must not become "today",
because the next level's clock starts from the date the plan answered
(29 CFR 2560.503-1 (i)(2)) — a date we made up here is a deadline shown to somebody
as the day they must act by.

`None` then travels to `CaseStore.record_response`, which raises with the reason. The
refusal is written in one place rather than paraphrased here, where the paraphrase
would drift.
"""

from __future__ import annotations

from datetime import date

from recourse.domain.types import Outcome

#: Everything except PENDING. "Pending" is the absence of an answer, so recording it
#: as one would close a clock that is still running.
ANSWERS: tuple[Outcome, ...] = (
    Outcome.OVERTURNED, Outcome.PARTLY_OVERTURNED, Outcome.UPHELD,
)


def read_outcome(raw: str) -> Outcome | None:
    """One of the three real answers, or None for anything else."""
    try:
        found = Outcome(str(raw).strip().lower())
    except ValueError:
        return None
    return found if found in ANSWERS else None


def read_date(raw: str) -> date | None:
    """The date on the letter, or None — which the store then refuses."""
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None
