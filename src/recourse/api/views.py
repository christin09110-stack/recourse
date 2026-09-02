"""An appeal, as JSON, with every level it has been through.

`levels` and `history` are both sent. An ERISA plan may require two mandatory
internal appeals, and the second exists to contest what the first decided — so the
level-one letter, date and outcome are part of what the second argues against, not
superseded detail. A console given only the current stage cannot show that, and the
record it displays would be the one thing the appeal is about, missing.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from recourse.api.clocks_view import deadline_view, deadlines_of
from recourse.domain.appeal import Appeal, StageRecord
from recourse.domain.case import CaseFile
from recourse.domain.clocks import insurer_is_overdue, risk_for


def stage_view(record: StageRecord) -> dict[str, Any]:
    return {
        "stage": record.stage.value,
        "started_on": record.started_on.isoformat() if record.started_on else None,
        "sent_on": record.sent_on.isoformat() if record.sent_on else None,
        "answered_on": record.answered_on.isoformat() if record.answered_on else None,
        "outcome": record.outcome.value,
        "letter_body": record.letter_body,
        "assertions": [
            {"text": a.text, "clinical": a.clinical, "document_id": a.document_id}
            for a in record.assertions
        ],
    }


def appeal_view(case: CaseFile, appeal: Appeal, now: date, warn_days: int) -> dict[str, Any]:
    """One appeal: where it is, everywhere it has been, and both clocks."""
    deadlines = deadlines_of(case, appeal)
    return {
        "appeal_id": appeal.appeal_id,
        "denial_id": appeal.denial_id,
        "plan_id": appeal.plan_id,
        "stage": appeal.stage.value,
        "outcome": appeal.outcome.value,
        "is_open": appeal.is_open,
        "levels": [stage_view(level) for level in appeal.levels],
        "history": [stage_view(level) for level in appeal.history],
        "deadlines": deadline_view(deadlines),
        # "unassessable" rather than "ok" where the clocks could not be computed.
        # An unreadable plan type is not a plan that is on track.
        "risk": risk_for(deadlines, now, warn_days).value if deadlines else "unassessable",
        "days_remaining": (
            (deadlines.mine - now).days if deadlines and deadlines.mine else None
        ),
        "insurer_overdue": (
            insurer_is_overdue(deadlines, now, appeal.answered_on) if deadlines else False
        ),
    }
