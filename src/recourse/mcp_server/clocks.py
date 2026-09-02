"""The clocks, over the protocol, computed by the same pure functions as everything else.

There is no world behind MCP — no case file, no stored appeal — so the caller states
the facts a deadline depends on and gets arithmetic back. That is the whole point of
exposing this: the clocks are the reusable half of Recourse, and a claimant's
software should not have to reimplement 29 CFR 2560.503-1 to count to 180.

A `None` date means the clock has not started, never that it has run out. An ERISA
level-two appeal whose level one is unanswered genuinely has no date yet.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from recourse.domain.clocks import deadlines_for, insurer_is_overdue, risk_for
from recourse.domain.models import Plan
from recourse.domain.types import AppealStage, PlanType, ServiceType


def _plan(plan_type: str, internal_levels: int, grandfathered: bool) -> Plan:
    """A plan carrying only what a clock depends on. No identity, no case file."""
    return Plan(
        plan_id="mcp", name="mcp", plan_type=PlanType(plan_type), member_id="mcp",
        internal_levels=internal_levels, grandfathered=grandfathered,
    )


def _on(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def compute(
    plan_type: str, service_type: str, stage_started_on: str | None,
    stage: str = "internal_1", internal_levels: int = 1,
    grandfathered: bool = False, filed_on: str | None = None,
) -> Any:
    """The `Deadlines` object itself, so `risk` and `deadlines` cannot diverge."""
    return deadlines_for(
        plan=_plan(plan_type, internal_levels, grandfathered),
        service_type=ServiceType(service_type),
        stage=AppealStage(stage),
        stage_started_on=_on(stage_started_on),
        filed_on=_on(filed_on),
    )


def as_dict(deadlines: Any) -> dict[str, Any]:
    return {
        "stage": deadlines.stage.value,
        "my_deadline": deadlines.mine.isoformat() if deadlines.mine else None,
        "their_deadline": deadlines.theirs.isoformat() if deadlines.theirs else None,
        "next_stage": deadlines.next_stage.value if deadlines.next_stage else None,
        "next_stage_window_days": deadlines.next_stage_window_days,
        "basis": deadlines.basis,
        "citation": deadlines.citation,
    }


def risk(deadlines: Any, today: str, warn_days: int, answered_on: str | None) -> dict[str, Any]:
    """How close the claimant's clock is, and whether the plan has blown its own."""
    now = date.fromisoformat(today)
    return {
        **as_dict(deadlines),
        "today": today,
        "risk": risk_for(deadlines, now, warn_days).value,
        "days_remaining": (deadlines.mine - now).days if deadlines.mine else None,
        "insurer_overdue": insurer_is_overdue(deadlines, now, _on(answered_on)),
    }
