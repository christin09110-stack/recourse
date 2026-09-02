"""Assembling and running the PRESS agent — the clock, on a schedule.

This is the loop that runs when nobody asked it to. Every other guard in this system
waits to be provoked by a tool call; the obligation this loop serves fires because the
agent is about to do *nothing*, and doing nothing for six months is how a 180-day
window closes with the merits still intact and no longer mattering.

Two interventions, in the same order as WATCH and for the same reason: `CitationGuard`
first, because its `Deny` short-circuits and must never reach a policy that would
weigh an unsupported sentence on cost and urgency.

`checkpointing=False`, the snapshot preset and the resume rules are in `loops/run.py`,
with what each of them cost written down. Read that before changing anything here.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from typing import Any

from strands import Agent

from recourse.domain.types import AutonomyLevel
from recourse.hooks.audit import AuditTrail
from recourse.loops.press.board import Board
from recourse.loops.press.context import build_press_context_provider
from recourse.loops.press.prompt import SYSTEM_PROMPT
from recourse.loops.press.tools import build_press_tools
from recourse.loops.run import LoopRunResult, resume, run
from recourse.persistence.store import CaseStore
from recourse.policy.citation import CitationGuard
from recourse.policy.escalation import EscalationPolicy

MODEL_ID = os.environ.get("RECOURSE_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("RECOURSE_AWS_REGION", "us-east-1")


def build_default_policy(
    store: CaseStore, clock: Callable[[], date], level: AutonomyLevel,
) -> EscalationPolicy:
    return EscalationPolicy(level, build_press_context_provider(store, clock, level))


def build_press_agent(
    store: CaseStore,
    clock: Callable[[], date],
    policy: EscalationPolicy,
    trail: AuditTrail,
    level: AutonomyLevel = AutonomyLevel.BALANCED,
    notices: list[dict[str, Any]] | None = None,
    board: Board | None = None,
) -> Agent:
    return Agent(
        model=MODEL_ID,
        tools=build_press_tools(store, clock, level, notices, board),
        # Order is enforcement, not preference. See the module docstring.
        interventions=[CitationGuard(lambda: store.case), policy],
        hooks=[trail],
        system_prompt=SYSTEM_PROMPT,
        checkpointing=False,
        callback_handler=None,
    )


#: The standing instruction for a scheduled sweep. Nobody types this: PRESS runs when
#: nobody asked it to, which is the only way a 180-day window gets watched at all.
SWEEP = ("Sweep every open appeal. Raise anything whose deadline is close, anything "
         "already missed, and any appeal the plan is past its own limit to answer.")


async def run_press(state: Any) -> LoopRunResult:
    """Sweep every open appeal's clocks with a fresh agent."""
    policy = build_default_policy(state.store, state.world.now, state.autonomy)
    agent = build_press_agent(state.store, state.world.now, policy, state.trail,
                              state.autonomy)
    return await run(agent, SWEEP, policy)


async def resume_press(
    agent: Agent, snapshot: dict[str, Any], interrupt_id: str,
    decision_record: dict[str, Any], policy: EscalationPolicy,
) -> LoopRunResult:
    """Resume a paused sweep. **Only ever call this on an approval.**

    A decline must end the run in the caller's own code and never reach here. See
    `loops.run.resume` for what a resumed decline did in production: the run
    continued, the model did the thing the operator had refused, and the operator's
    name went on the record for it.
    """
    return await resume(agent, snapshot, interrupt_id, decision_record, policy)
