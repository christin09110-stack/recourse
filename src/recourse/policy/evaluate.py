"""Judging one proposed action against the dial.

Kept apart from the rules themselves so that the three non-negotiables read as a
declaration in `rules.py` rather than as branches buried in a function.
"""

from __future__ import annotations

from recourse.domain.types import AutonomyLevel
from recourse.policy.rules import THRESHOLDS, ActionContext, RuleHit

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
    # A closing deadline and a late insurer are NOT reasons to stop a tool call.
    # They are reasons to speak, and `policy.sweep` speaks: it raises them on a
    # schedule, at every autonomy level, whether or not the agent is doing anything.
    #
    # Blocking here was backwards and it showed on the first live run. Drafting a
    # letter for the one appeal whose insurer was nineteen days late got held for a
    # human, because being late was reported as a rule against acting. The moment a
    # window is closing is the moment to want the draft written, not to stop it.
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
