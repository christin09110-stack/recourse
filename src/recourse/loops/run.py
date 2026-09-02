"""Running a loop, parking it on a Confirm, and resuming the same run afterwards.

Shared by WATCH and PRESS because the failures it guards against are not specific to
either, and a second copy is a second place to get them wrong. Every one of these was
paid for in Muster.

**`checkpointing=False`, always.** `checkpointing=True` stops the run *before* the
tool call and hands back `result.interrupts is None`, so the escalation looks like a
completed run that did nothing. Human-in-the-loop breaks silently.

**`take_snapshot(preset="session")`.** Bare, it raises `SnapshotException("No
snapshot fields resolved")` — on the escalation path, which is the one path that must
never fail.

**The interrupt's fields are read directly.** They are `id` and `reason`. Muster
reached for `interrupt_id` and `prompt` through `getattr(..., None)`, so a wrong name
produced a cheerful `None` instead of an error and the resume failed hours later,
after the person had answered and their decision had been consumed. Read them
directly, so an SDK rename breaks here, loudly, rather than there, silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strands import Agent, Snapshot

from recourse.policy.escalation import EscalationPolicy, proposal_that_paused, rules_that_paused


@dataclass
class LoopRunResult:
    paused: bool
    interrupt_id: str | None
    interrupt_reason: str | None
    snapshot: dict[str, Any] | None
    text: str
    rule_hits: list[dict[str, str]] = field(default_factory=list)
    #: The guarded call the person is being asked about, arguments and all, so the
    #: question can name the denial rather than asking "approve this?" about nothing.
    proposal: dict[str, Any] = field(default_factory=dict)


def result_from(agent: Agent, raw: Any, policy: EscalationPolicy) -> LoopRunResult:
    """Build a result, reading the interrupt's real fields. See the module docstring."""
    interrupts = getattr(raw, "interrupts", None) or []
    if not interrupts:
        return LoopRunResult(False, None, None, None, str(raw))
    interrupt = interrupts[0]
    hits = rules_that_paused(raw, policy)
    return LoopRunResult(
        paused=True,
        interrupt_id=interrupt.id,
        interrupt_reason=hits[0].rule if hits else "unknown",
        snapshot=agent.take_snapshot(preset="session").__dict__,
        text=interrupt.reason or str(raw),
        rule_hits=[{"rule": h.rule, "detail": h.detail} for h in hits],
        proposal=proposal_that_paused(raw, policy),
    )


async def run(agent: Agent, prompt: str, policy: EscalationPolicy) -> LoopRunResult:
    return result_from(agent, await agent.invoke_async(prompt), policy)


async def resume(
    agent: Agent,
    snapshot: dict[str, Any],
    interrupt_id: str,
    decision_record: dict[str, Any],
    policy: EscalationPolicy,
) -> LoopRunResult:
    """Resume a paused run with a person's approval.

    **Call this only when the person approved.** A decline must end the run in the
    caller's own code and never reach here, because handing a refusal back to the
    agent hands the refused call back to the agent. In Muster the SDK's `evaluate`
    callback did not hold the decline: the run resumed, the model tried the same
    thing again, and the operator's name went on the receipt for a change they had
    explicitly refused. The safe boundary is not inside the agent, so it is here: the
    caller decides, and declining means not calling this function at all.

    `decision_record` is the structured answer — outcome, who decided, their
    relationship to the patient, their note — because all of that belongs in the
    journal. `policy.approves` is what reads it back on the SDK's side.
    """
    agent.load_snapshot(Snapshot(**snapshot))
    raw = await agent.invoke_async(
        [{"interruptResponse": {"interruptId": interrupt_id, "response": decision_record}}]
    )
    return result_from(agent, raw, policy)
