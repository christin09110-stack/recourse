# tests/adapters/conftest.py
"""Shared handles on the seeded world, so each test file states only its own point."""

from __future__ import annotations

import pytest

from recourse.adapters.simulated import SimulatedWorld
from recourse.domain.appeal import Appeal, Deadlines
from recourse.domain.case import CaseFile
from recourse.domain.clocks import deadlines_for


@pytest.fixture
def world() -> SimulatedWorld:
    return SimulatedWorld()


@pytest.fixture
def case(world: SimulatedWorld) -> CaseFile:
    return world.case_file()


def deadlines_of(case: CaseFile, appeal: Appeal) -> Deadlines:
    """The clocks for one seeded appeal, through the same function the console uses."""
    claim = case.claims[case.denials[appeal.denial_id].claim_id]
    return deadlines_for(
        plan=case.plans[appeal.plan_id],
        service_type=claim.service_type,
        stage=appeal.stage,
        stage_started_on=appeal.stage_started_on,
        filed_on=appeal.sent_on,
    )
