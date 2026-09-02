"""A parked question, said in terms the person answering it can act on.

The `subject` block is the part that matters. The policy stops one specific call
about one specific denial, and a console that showed only the rule and the prompt
asked somebody to approve a sentence with no answer to "about which claim". Muster
shipped exactly that: an escalation rendered with an em dash where the name belongs.

`severity` is carried through because a deadline escalation gets louder the longer
it goes unanswered, and a queue that displayed every question at the same weight
would hide the one that is running out of time.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.case import CaseFile
from recourse.persistence.decisions import PendingDecision


def _subject(case: CaseFile, appeal_id: str) -> dict[str, Any]:
    """Which denial this question is about, in words a person recognises."""
    appeal = case.appeals.get(appeal_id)
    denial = case.denials.get(appeal.denial_id) if appeal else None
    line = case.line(denial.line_id) if denial else None
    return {
        "appeal_id": appeal_id or None,
        "denial_id": denial.denial_id if denial else None,
        "denial_class": denial.denial_class.value if denial else None,
        "matched_code": denial.matched_code if denial else None,
        "provider": line.provider if line else None,
        "description": line.description if line else None,
        "amount": line.patient_responsibility.dollars if line else None,
    }


def pending_view(pending: PendingDecision, case: CaseFile) -> dict[str, Any]:
    decision = pending.decision
    return {
        "decision_id": decision.decision_id,
        "rule": decision.rule,
        "prompt": decision.prompt,
        "severity": pending.severity,
        "rule_hits": pending.rule_hits,
        "proposal": pending.proposal or None,
        "subject": _subject(case, decision.appeal_id),
        "outcome": decision.outcome.value if decision.outcome else None,
        "by": decision.by,
        "role": decision.role,
        "note": decision.note,
        "at": decision.at.isoformat() if decision.at else None,
    }
