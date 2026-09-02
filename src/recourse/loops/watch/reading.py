"""The three WATCH tools that only look: what is denied, why, and what it needs.

Every classification comes from `codes.classify` and every date from `clocks`, so the
sentence the model reads is computed by the same functions the escalation policy
judges it with. The model is never the source of a class or a date; it only chooses
what to do about one.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from strands import tool

from recourse.domain.case import CaseFile
from recourse.domain.evidence import can_prepare_alone, gaps, requirements_for
from recourse.domain.models import Denial
from recourse.loops.lookup import deadlines_at_notice, resolve_denial
from recourse.persistence.store import CaseStore


def _row(case: CaseFile, denial: Denial) -> dict[str, Any]:
    line = case.line(denial.line_id)
    return {
        "denial_id": denial.denial_id,
        "claim_id": denial.claim_id,
        "denial_class": denial.denial_class.value,
        "carc": denial.matched_code,
        "service": line.description if line else "",
        "amount_at_stake": str(line.patient_responsibility) if line else "",
        "reason": denial.reason_text,
    }


def build_reading_tools(store: CaseStore, clock: Callable[[], date]) -> list[Any]:
    @tool
    def list_denials() -> Any:
        """Every denied line in the case file, with its class and what is at stake."""
        case = store.case
        return [_row(case, denial) for denial in case.denials.values()]

    @tool
    def explain_denial(denial_id: str) -> Any:
        """What this denial's own code means, and every clock now running on it."""
        resolved, error = resolve_denial(store.case, denial_id)
        if error:
            return {"error": error}
        clocks = deadlines_at_notice(resolved)
        if clocks is None:
            # A plan type with no clock table is refused, never defaulted: the health
            # figure on a non-health plan would promise four months nobody has.
            return {"error": f"no clock table ships for plan type "
                             f"{resolved.plan.plan_type.value!r}, so this denial's "
                             "deadlines cannot be computed and must not be guessed"}
        return {
            "denial_id": denial_id,
            "carc": resolved.denial.matched_code,
            "denial_class": resolved.denial.denial_class.value,
            "reason": resolved.denial.reason_text,
            "notice_date": resolved.claim.notice_date.isoformat(),
            "my_deadline": clocks.mine.isoformat() if clocks.mine else None,
            "days_remaining": (clocks.mine - clock()).days if clocks.mine else None,
            "basis": clocks.basis,
            "citation": clocks.citation,
            "next_stage": clocks.next_stage.value if clocks.next_stage else None,
        }

    @tool
    def check_evidence(denial_id: str) -> Any:
        """What an appeal of this class needs, and what the case file cannot supply."""
        resolved, error = resolve_denial(store.case, denial_id)
        if error:
            return {"error": error}
        found = resolved.denial.denial_class
        return {
            "denial_id": denial_id,
            "denial_class": found.value,
            "needs": [{"kind": r.kind, "why": r.why, "required": r.required}
                      for r in requirements_for(found)],
            "missing": [{"kind": r.kind, "why": r.why} for r in gaps(store.case, found)],
            # False for every clinical denial, letter on file or not. The gap there is
            # authorship, not paperwork: the argument is the treating clinician's.
            "can_prepare_alone": can_prepare_alone(store.case, found),
        }

    return [list_denials, explain_denial, check_evidence]
