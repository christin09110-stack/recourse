"""Which pause is this, and what was it about.

Split from `escalation.py` for size; it reads that policy's own bookkeeping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from recourse.policy.rules import RuleHit

if TYPE_CHECKING:  # circular at runtime, and only the annotations need it
    from recourse.policy.escalation import EscalationPolicy


def _hits_and_proposal(
    result: Any, policy: EscalationPolicy,
) -> tuple[list[RuleHit], dict[str, Any]]:
    """Match the interrupt that stopped this run to what the policy recorded.

    Read by tool-use id rather than from `last_hits`, because a run can clear a guard
    on one call and pause on a later one, and `last_hits` would by then describe the
    wrong call — the wrong denial, the wrong deadline, the wrong question.
    """
    for interrupt in getattr(result, "interrupts", None) or []:
        # Interrupt.id looks like
        #   "v1:before_tool_call:tooluse_R0kIpR...:b174861a-..."
        # so the tool-use id the policy keyed on is embedded rather than exposed as
        # its own attribute. Match on containment, and never invent an attribute name
        # the SDK does not have.
        # Longest id first. Containment means a short id ("tu-1") also matches an
        # interrupt belonging to a longer one ("tu-10"), and dict order would decide
        # which pause the console described. Muster matches in insertion order and
        # has the same latent ambiguity; its ids are long enough to hide it.
        for tool_use_id, hits in sorted(policy.escalations.items(), key=lambda kv: -len(kv[0])):
            if tool_use_id and tool_use_id in str(interrupt.id):
                return hits, policy.proposals.get(tool_use_id, {})
    return policy.last_hits, {}


def proposal_that_paused(result: Any, policy: EscalationPolicy) -> dict[str, Any]:
    """The tool call the person is being asked about, arguments and all."""
    return _hits_and_proposal(result, policy)[1]


def rules_that_paused(result: Any, policy: EscalationPolicy) -> list[RuleHit]:
    """The hits belonging to the interrupt that actually stopped this run."""
    return _hits_and_proposal(result, policy)[0]
