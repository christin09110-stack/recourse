"""The autonomy boundary, as a Strands intervention.

Runs before every consequential tool call and returns Proceed or Confirm. A Confirm
breaks the agent out of its loop so the run can be parked until a person answers.

**`CitationGuard` is ordered before this handler** and its `Deny` short-circuits. An
appeal sentence the record does not support must never arrive here, because this
policy would weigh it on money, urgency and autonomy level — none of which has an
opinion about whether the sentence is true — and let it through.

Build one instance per run. `last_hits`, `escalations` and `proposals` are
per-instance mutable state that callers read after the run returns; two runs sharing
a policy would attribute one case's escalation reason to the other.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from strands import InterventionHandler
from strands.interventions.actions import Confirm, Proceed

from recourse.domain.types import AutonomyLevel
from recourse.policy.approval import approves
from recourse.policy.evaluate import evaluate
from recourse.policy.paused import proposal_that_paused, rules_that_paused
from recourse.policy.rules import ActionContext, RuleHit

#: Tools that reach a person or commit something. Everything else is reading.
#:
#: There is no tool here that files an appeal, because there is no such tool anywhere
#: in this system. Filing is a legal act taken in the patient's name; the furthest
#: this agent goes is a drafted body marked ready to send, and a person sends it. A
#: guard would be the wrong shape for that rule — it is enforced by the absence of
#: the capability, which no autonomy level and no approval can restore.
GUARDED_TOOLS: frozenset[str] = frozenset({
    "draft_letter_body", "mark_ready_to_send", "request_document",
    "notify_person", "record_response", "advance_stage",
})

UNASSESSABLE = "unassessable"


class EscalationPolicy(InterventionHandler):
    name = "recourse-escalation"

    def __init__(
        self,
        level: AutonomyLevel,
        context_provider: Callable[[str, dict[str, Any]], ActionContext | None],
    ) -> None:
        self.level = level
        self.context_provider = context_provider
        self.last_hits: list[RuleHit] = []
        self.escalations: dict[str, list[RuleHit]] = {}
        #: tool-use id -> the call that was stopped, so the question put to the person
        #: can name the claim it is about. Without it the console asks "approve this?"
        #: with the rule and the deadline, and no answer to "about which denial".
        self.proposals: dict[str, dict[str, Any]] = {}

    def before_tool_call(self, event: Any, **kwargs: Any) -> Any:
        tool_name = event.tool_use["name"]
        if tool_name not in GUARDED_TOOLS:
            return Proceed(reason="tool commits nothing and reaches nobody")

        args = event.tool_use.get("input", {}) or {}
        context = self.context_provider(tool_name, args)
        if context is None:
            # Unknown is never benign here: an unreadable code, a plan with no clock
            # table, a missing notice date. None of them is "no action needed".
            hits = [RuleHit(
                UNASSESSABLE,
                f"Recourse cannot judge the effect of {tool_name.replace('_', ' ')} "
                "on this case, so it will not do it unattended.",
            )]
        else:
            hits = evaluate(context, self.level)

        if not hits:
            self.last_hits = []
            return Proceed(reason=f"within the {self.level.value} limits")

        self.last_hits = hits
        tool_use_id = event.tool_use.get("toolUseId", "")
        self.escalations[tool_use_id] = hits
        self.proposals[tool_use_id] = {"tool": tool_name, **args}
        return Confirm(
            prompt=" ".join(hit.detail for hit in hits) + " Approve this?",
            reason=hits[0].rule,
            evaluate=approves,
        )

#: Re-exported so callers read one module: the policy and the two questions asked of
#: its record after a run returns.
__all__ = ["GUARDED_TOOLS", "EscalationPolicy", "approves",
           "proposal_that_paused", "rules_that_paused"]
