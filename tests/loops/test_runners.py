"""How both agents are assembled, and how a paused run is read and resumed.

Every assertion here is a bug that was paid for once already, in Muster, and none of
them fails loudly on its own: checkpointing breaks human-in-the-loop silently, the
wrong interrupt attribute reads as `None` hours later, and a bare snapshot raises on
the one path that must never fail.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from strands.interrupt import Interrupt

from recourse.domain.types import AutonomyLevel
from recourse.hooks.audit import AuditTrail
from recourse.loops.press import runner as press_runner
from recourse.loops.run import result_from
from recourse.loops.watch import runner as watch_runner
from recourse.policy.rules import RuleHit
from tests.loops.support import seeded

LEVEL = AutonomyLevel.BALANCED


def _watch_agent():
    world, store = seeded()
    policy = watch_runner.build_default_policy(store, world.now, LEVEL)
    return watch_runner.build_watch_agent(store, world.now, policy, AuditTrail()), policy


def _press_agent():
    world, store = seeded()
    policy = press_runner.build_default_policy(store, world.now, LEVEL)
    return press_runner.build_press_agent(store, world.now, policy, AuditTrail(), LEVEL), policy


@pytest.mark.parametrize("build", [_watch_agent, _press_agent])
def test_both_agents_are_built_with_checkpointing_off(build):
    """checkpointing=True stops the run before the tool call and returns no interrupts.

    strands-agents==1.54.0 keeps this on a private field; there is no public
    `Agent.checkpointing` to read.
    """
    agent, _ = build()
    assert agent._checkpointing is False


@pytest.mark.parametrize("build", [_watch_agent, _press_agent])
def test_the_citation_guard_runs_before_the_escalation_policy(build):
    """A Deny must short-circuit. A policy that saw the call first would weigh an
    unsupported clinical sentence on money and urgency and find nothing wrong."""
    agent, _ = build()
    names = [type(i).__name__ for i in agent._intervention_registry.handlers]
    assert names.index("CitationGuard") < names.index("EscalationPolicy")


def test_the_result_reads_the_interrupts_real_fields():
    """Pins the SDK's field names so a rename fails here, not at resume time.

    Muster reached for `interrupt.interrupt_id` and `interrupt.prompt` through
    `getattr(..., default)`. Neither exists on `strands.interrupt.Interrupt`, so both
    produced a cheerful None — and the resume failed with `interrupt_id=<None> | no
    interrupt found` only after a person had answered and their decision had been
    consumed.
    """
    agent, policy = _watch_agent()
    interrupt = Interrupt(id="v1:before_tool_call:tooluse_ABC:xyz",
                          name="recourse-escalation",
                          reason="30 days remain to appeal.")
    policy.escalations["tooluse_ABC"] = [RuleHit("deadline_at_risk", "30 days remain.")]

    result = result_from(agent, SimpleNamespace(interrupts=[interrupt]), policy)

    assert result.paused is True
    assert result.interrupt_id == "v1:before_tool_call:tooluse_ABC:xyz"
    assert result.text == "30 days remain to appeal."
    assert result.interrupt_reason == "deadline_at_risk"
    # take_snapshot(preset="session") — bare it raises, on the escalation path.
    assert result.snapshot is not None


def test_a_run_that_was_not_stopped_carries_no_snapshot_and_no_interrupt():
    agent, policy = _press_agent()
    result = result_from(agent, SimpleNamespace(interrupts=[]), policy)
    assert result.paused is False
    assert result.interrupt_id is None and result.snapshot is None
