"""The clocks, as JSON.

Recomputed here from the pure functions rather than read off anything stored, so a
date on the screen is the same date the policy judges and the letter quotes. A
cached deadline is one that can drift out of step with the engine, and it would
drift in the reassuring direction.

`stage_started_on` and `sent_on` go to `deadlines_for` separately on purpose: the
claimant's window runs from the notice date, and the plan's own window runs from the
day the appeal was posted. Passing the notice date for both reported an insurer as
months late answering a letter nobody had sent them.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.appeal import Appeal, Deadlines
from recourse.domain.case import CaseFile
from recourse.domain.clocks import deadlines_for
from recourse.policy.finding import Finding
from recourse.rulebook.loader import PlanTypeNotInScope


def deadlines_of(case: CaseFile, appeal: Appeal) -> Deadlines | None:
    """The clocks on one appeal, or `None` where they cannot honestly be computed.

    `None` is the answer for a plan type with no clock table and for an appeal whose
    claim or plan the file cannot resolve. It is never a default: the caller reports
    it as unassessable rather than showing a plausible wrong date.
    """
    denial = case.denials.get(appeal.denial_id)
    claim = case.claim_for_line(denial.line_id) if denial else None
    plan = case.plans.get(appeal.plan_id)
    if claim is None or plan is None:
        return None
    try:
        return deadlines_for(
            plan=plan, service_type=claim.service_type, stage=appeal.stage,
            stage_started_on=appeal.stage_started_on, filed_on=appeal.sent_on,
        )
    except PlanTypeNotInScope:
        return None


def deadline_view(deadlines: Deadlines | None) -> dict[str, Any] | None:
    if deadlines is None:
        return None
    return {
        "stage": deadlines.stage.value,
        "mine": deadlines.mine.isoformat() if deadlines.mine else None,
        "theirs": deadlines.theirs.isoformat() if deadlines.theirs else None,
        "next_stage": deadlines.next_stage.value if deadlines.next_stage else None,
        "next_stage_window_days": deadlines.next_stage_window_days,
        "basis": deadlines.basis,
        "citation": deadlines.citation,
    }


def finding_view(case: CaseFile, finding: Finding) -> dict[str, Any]:
    """One sweep finding. `sentence` is what a person is actually told."""
    denial = case.denials.get(finding.appeal.denial_id)
    claim = case.claim_for_line(denial.line_id) if denial else None
    return {
        "appeal_id": finding.appeal.appeal_id,
        "denial_id": finding.appeal.denial_id,
        "provider": claim.provider if claim else None,
        "risk": finding.risk.value,
        "days_remaining": finding.days_remaining,
        "insurer_overdue": finding.insurer_overdue,
        "needs_raising": finding.needs_raising,
        "sentence": finding.sentence,
        "deadlines": deadline_view(finding.deadlines),
    }
