"""The four denials, and the three appeals already running against them.

Nothing here states what a denial *means*. Every `Denial` is built by handing the
line's own CARCs and RARCs to `codes.classify`, so the seed cannot disagree with the
code table: if a row moves class, the demo moves with it rather than showing a label
the engine would contradict on screen. The ids are named for the code because that
is what a viewer is looking at.

The two appeals the demo turns on are placed by offset, not by date:

* `appeal-50` sits at day 150 of its 180-day filing window and has never been sent,
  because the argument belongs to the surgeon and the letter has not come. With a
  30-day warning window that is exactly where `risk_for` first says APPROACHING.
* `appeal-16` was sent, and Harbor Blue has now been silent for 19 days past the 60
  it had to answer. That clock runs against the insurer, and nobody but the claimant
  is counting it.

`appeal-197` is the healthy one, opened a fortnight ago and well inside every limit,
so the deadline screen is not uniformly on fire.
"""

from __future__ import annotations

from recourse.adapters.frozen import (
    DAYS_INTO_FILING_WINDOW,
    DAYS_SINCE_APPEAL_SENT,
    DAYS_SINCE_UNANSWERED_NOTICE,
    ago,
)
from recourse.adapters.seed_plans import PLAN_ACA, PLAN_ERISA
from recourse.domain.appeal import Appeal
from recourse.domain.codes import classify
from recourse.domain.models import Claim, Denial
from recourse.domain.types import AppealStage, Outcome

#: line id -> denial id. Named for the CARC, which is what the console shows.
_DENIAL_IDS = {
    "line-anesthesia": "den-16",
    "line-mri": "den-197",
    "line-homehealth": "den-50",
    "line-physio-visits": "den-96",
}


def denials(claims: dict[str, Claim]) -> dict[str, Denial]:
    """One `Denial` per refused line, classified by the engine rather than by hand."""
    built: dict[str, Denial] = {}
    for claim in claims.values():
        for line in claim.denied_lines:
            found = classify(line.carc, line.rarc)
            denial_id = _DENIAL_IDS[line.line_id]
            built[denial_id] = Denial(
                denial_id=denial_id,
                claim_id=claim.claim_id,
                line_id=line.line_id,
                denial_class=found.denial_class,
                # The CARC row, not the RARC that narrowed it: the letter contests
                # the adjustment code the insurer applied.
                matched_code=found.matched.code if found.matched else "",
                reason_text=found.reason,
            )
    return built


def appeals() -> dict[str, Appeal]:
    """Three open appeals: one at risk, one the insurer has ignored, one healthy."""
    return {
        "appeal-50": Appeal.opened(
            appeal_id="appeal-50", denial_id="den-50", plan_id=PLAN_ACA,
            stage=AppealStage.INTERNAL_1, outcome=Outcome.PENDING,
            started_on=ago(DAYS_INTO_FILING_WINDOW),
            # Drafted and not sent, on purpose. `Deadlines.mine` is the window to
            # file, so an unsent appeal at day 150 is the alarm, not a formality.
            sent_on=None,
        ),
        "appeal-16": Appeal.opened(
            appeal_id="appeal-16", denial_id="den-16", plan_id=PLAN_ACA,
            stage=AppealStage.INTERNAL_1, outcome=Outcome.PENDING,
            started_on=ago(DAYS_SINCE_UNANSWERED_NOTICE),
            sent_on=ago(DAYS_SINCE_APPEAL_SENT),
            # Unanswered is the whole point: `insurer_is_overdue` returns False the
            # moment this is set, so the demo's second clock lives on it staying None.
            answered_on=None,
        ),
        "appeal-197": Appeal.opened(
            appeal_id="appeal-197", denial_id="den-197", plan_id=PLAN_ERISA,
            stage=AppealStage.INTERNAL_1, outcome=Outcome.PENDING,
            started_on=ago(13), sent_on=ago(7),
        ),
    }
