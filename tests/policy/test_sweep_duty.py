"""The duty itself, now that it lives only in the sweep."""

from __future__ import annotations

import pytest

from recourse.domain.types import AutonomyLevel, DeadlineRisk
from recourse.policy.sweep import raisable, sweep
from tests.evals.support import seeded


@pytest.mark.parametrize("level", list(AutonomyLevel))
def test_a_closing_window_is_raised_at_every_autonomy_level(level):
    """No setting makes it quieter about a clock running out. The dial governs what
    the agent does; warning is not doing anything to anybody."""
    world, case = seeded()
    raised = raisable(sweep(case, world.now(), level))
    assert any(f.risk is not DeadlineRisk.OK or f.insurer_overdue for f in raised)


def test_the_sweep_speaks_without_being_asked():
    """Every other rule waits to be provoked by a tool call. A background agent
    that only spoke when provoked would go quiet through six months of a 180-day
    window and be right about everything except the thing that mattered."""
    world, case = seeded()
    assert raisable(sweep(case, world.now())), "nothing raised on a world that has a closing window"
