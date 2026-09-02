"""Assembling and running the WATCH agent — triage, on a denial arriving.

Two interventions, in this order. `CitationGuard` goes first because its `Deny`
short-circuits: a clinical sentence the record does not support must be refused
outright and never reach the escalation policy, which would weigh it on the deadline,
the amount and the autonomy level — none of which has an opinion about whether the
sentence is true — and let it through.

`checkpointing=False`, and the resume mechanics, are in `loops/run.py` with the
reasons written down. Read that before changing anything here.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from typing import Any

from strands import Agent

from recourse.domain.types import AutonomyLevel
from recourse.hooks.audit import AuditTrail
from recourse.loops.run import LoopRunResult, resume, run
from recourse.loops.watch.context import build_watch_context_provider
from recourse.loops.watch.prompt import SYSTEM_PROMPT
from recourse.loops.watch.tools import build_watch_tools
from recourse.persistence.store import CaseStore
from recourse.policy.citation import CitationGuard
from recourse.policy.escalation import EscalationPolicy

MODEL_ID = os.environ.get("RECOURSE_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("RECOURSE_AWS_REGION", "us-east-1")


def build_default_policy(
    store: CaseStore, clock: Callable[[], date], level: AutonomyLevel,
    prompted: bool = False,
) -> EscalationPolicy:
    return EscalationPolicy(level, build_watch_context_provider(store, clock, level, prompted))


def build_watch_agent(
    store: CaseStore,
    clock: Callable[[], date],
    policy: EscalationPolicy,
    trail: AuditTrail,
    requests: list[dict[str, Any]] | None = None,
) -> Agent:
    return Agent(
        model=MODEL_ID,
        tools=build_watch_tools(store, clock, requests),
        # Order is enforcement, not preference. See the module docstring.
        interventions=[CitationGuard(lambda: store.case), policy],
        hooks=[trail],
        system_prompt=SYSTEM_PROMPT,
        checkpointing=False,
        callback_handler=None,
    )


#: What a person clicking Triage is actually asking for. A standing instruction
#: rather than free text, so a recorded demo and a scheduled run do the same thing.
TRIAGE = ("Triage every denial in this case file. Explain each one, check what the "
          "file already holds, and draft the appeals the evidence supports.")


async def run_watch(state: Any) -> LoopRunResult:
    """Triage the case file with a fresh agent. The control plane's entry point.

    `prompted=True`: a person asked for this, so the autonomy dial's "draft only
    when asked" setting is satisfied by the request itself.
    """
    policy = build_default_policy(state.store, state.world.now, state.autonomy,
                                  prompted=True)
    agent = build_watch_agent(state.store, state.world.now, policy, state.trail)
    return await run(agent, TRIAGE, policy)


async def resume_watch(
    agent: Agent, snapshot: dict[str, Any], interrupt_id: str,
    decision_record: dict[str, Any], policy: EscalationPolicy,
) -> LoopRunResult:
    """Resume a paused triage. **Only ever call this on an approval** — see
    `loops.run.resume`, which explains what a resumed decline did in production."""
    return await resume(agent, snapshot, interrupt_id, decision_record, policy)
