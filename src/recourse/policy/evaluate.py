"""Judging one proposed action against the dial.

Kept apart from the rules themselves so that the three non-negotiables read as a
declaration in `rules.py` rather than as branches buried in a function.
"""

from __future__ import annotations

from recourse.domain.types import AutonomyLevel, DeadlineRisk
from recourse.policy.rules import THRESHOLDS, ActionContext, RuleHit

#: Risks that mean the clock is close enough that a person must be told now.
_AT_RISK = (DeadlineRisk.APPROACHING, DeadlineRisk.CRITICAL, DeadlineRisk.MISSED)


def _deadline_detail(context: ActionContext) -> str:
    if context.risk is DeadlineRisk.MISSED:
        return ("The window to appeal has closed. Nothing about the merits of this "
                "claim matters now, and that is why it was never allowed to pass "
                "quietly.")
    left = context.days_remaining
    counted = f"{left} days remain" if left is not None else "the window is closing"
    return f"{counted} to appeal, and nobody else in this process is counting them."


def evaluate(context: ActionContext, level: AutonomyLevel) -> list[RuleHit]:
    """Every rule this action trips at this autonomy level."""
    if not context.assessable:
        return [RuleHit(
            "unassessable",
            "Recourse cannot read the plan, the codes or the dates well enough to "
            "judge this, so it will not act on it unattended.",
        )]

    limits = THRESHOLDS[level]
    hits: list[RuleHit] = []

    if context.uncited_clinical:
        hits.append(RuleHit(
            "uncited_clinical_assertion",
            "This would state something clinical that no document in the file "
            "supports: " + "; ".join(repr(t) for t in context.uncited_clinical),
        ))
    if context.would_file:
        hits.append(RuleHit(
            "filing_is_not_the_agents",
            "Filing an appeal is a legal act in the claimant's name. Recourse "
            "prepares it; a person sends it.",
        ))
    if context.risk in _AT_RISK:
        hits.append(RuleHit("deadline_at_risk", _deadline_detail(context)))
    elif context.insurer_overdue:
        # Not at every level of urgency, but always worth saying: it is the one
        # clock in this process running against the plan rather than the claimant.
        hits.append(RuleHit(
            "insurer_overdue",
            "The plan is past its own deadline to answer this appeal.",
        ))

    if context.reaches_a_third_party and not limits.may_request_records:
        hits.append(RuleHit(
            "records_request_needs_you",
            f"This asks a provider or plan for records in the claimant's name, and "
            f"{level.value} does not allow that unattended.",
        ))
    if context.unprompted_draft and not limits.may_draft_unprompted:
        hits.append(RuleHit(
            "draft_needs_you",
            f"{level.value} does not draft without being asked.",
        ))
    return hits
