"""Resolving a denial to everything a tool needs, and the clocks that hang off it.

Both loops start from the same question — which claim, which line, which plan, which
appeal — and both must answer it the same way, because a tool that resolved a denial
differently from the policy judging that tool would let the model see one world and
the guard judge another.

Nothing here raises. A tool answers the model with an `{"error": ...}` dict and a
context provider answers the policy with `None`; a traceback out of a tool is a run
that stops with no record of why.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.appeal import Appeal, Deadlines
from recourse.domain.case import CaseFile
from recourse.domain.clocks import deadlines_for
from recourse.domain.models import Claim, ClaimLine, Denial, Plan
from recourse.domain.types import AppealStage
from recourse.rulebook.loader import PlanTypeNotInScope


@dataclass(frozen=True)
class Resolved:
    """One denial and everything about it that is a fact of the record."""

    denial: Denial
    claim: Claim
    line: ClaimLine
    plan: Plan
    appeal: Appeal | None


def appeal_for_denial(case: CaseFile, denial_id: str) -> Appeal | None:
    return next((a for a in case.appeals.values() if a.denial_id == denial_id), None)


def resolve_denial(case: CaseFile, denial_id: str) -> tuple[Resolved | None, str | None]:
    """Everything `denial_id` needs, or a refusal a tool can hand straight back."""
    denial = case.denials.get(denial_id)
    if denial is None:
        return None, f"unknown denial_id {denial_id!r}; call list_denials first"
    claim, line = case.claim_for_line(denial.line_id), case.line(denial.line_id)
    if claim is None or line is None:
        return None, f"denial {denial_id!r} names a claim line this case file does not hold"
    plan = case.plans.get(claim.plan_id)
    if plan is None:
        return None, f"claim {claim.claim_id!r} names an unknown plan {claim.plan_id!r}"
    return Resolved(denial, claim, line, plan, appeal_for_denial(case, denial_id)), None


def _clocks(plan: Plan, claim: Claim, stage: AppealStage,
            started_on, filed_on) -> Deadlines | None:
    try:
        return deadlines_for(plan=plan, service_type=claim.service_type, stage=stage,
                             stage_started_on=started_on, filed_on=filed_on)
    except PlanTypeNotInScope:
        # Not a default and not a substitution — the loader's refusal becomes
        # "unassessable", which escalates to a person. The one thing that must never
        # happen is a plausible date computed from a table we do not have.
        return None


def deadlines_at_notice(resolved: Resolved) -> Deadlines | None:
    """The clocks a denial runs on before anybody has opened an appeal against it.

    Counted from the notice date, which is what the regulation counts from, and with
    no `filed_on`: an unsent appeal has started nobody's clock but the claimant's.
    """
    return _clocks(resolved.plan, resolved.claim, AppealStage.INTERNAL_1,
                   resolved.claim.notice_date, None)


def deadlines_of(case: CaseFile, appeal: Appeal) -> Deadlines | None:
    """The clocks on one live appeal at the stage it has actually reached."""
    denial = case.denials.get(appeal.denial_id)
    claim = case.claim_for_line(denial.line_id) if denial else None
    plan = case.plans.get(appeal.plan_id)
    if claim is None or plan is None:
        return None
    return _clocks(plan, claim, appeal.stage, appeal.stage_started_on, appeal.sent_on)
