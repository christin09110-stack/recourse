"""The two clock tools: the dates, and how close they are.

Both compute through `clocks.compute`, so `check_risk` can never report a risk
against a different deadline from the one `deadlines_for` returns for the same facts.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from recourse.mcp_server import clocks


def add_clock_tools(server: FastMCP) -> None:
    @server.tool()
    def deadlines_for(
        plan_type: str, service_type: str, notice_date: str,
        stage: str = "internal_1", internal_levels: int = 1,
        grandfathered: bool = False, filed_on: str | None = None,
    ) -> dict[str, Any]:
        """Every date attached to one appeal: the claimant's deadline to file, the
        plan's deadline to answer, and what follows this stage. `plan_type` is
        `aca_marketplace` or `erisa_group_health`; `service_type` is `urgent`,
        `pre_service` or `post_service`; dates are ISO (YYYY-MM-DD). `notice_date` is
        the date on the denial for a first-level appeal and the date the previous
        level was answered for anything after it. `filed_on` is when the appeal was
        actually posted, which is what the plan's own clock runs from. A null date
        means that clock has not started, not that it has run out."""
        return clocks.as_dict(clocks.compute(
            plan_type, service_type, notice_date, stage, internal_levels,
            grandfathered, filed_on,
        ))

    @server.tool()
    def check_risk(
        plan_type: str, service_type: str, notice_date: str, today: str,
        warn_days: int = 45, stage: str = "internal_1", internal_levels: int = 1,
        grandfathered: bool = False, filed_on: str | None = None,
        answered_on: str | None = None,
    ) -> dict[str, Any]:
        """How close an appeal is to its deadline — ok, approaching, critical or
        missed — how many days remain, and whether the plan is past its own deadline
        to answer. `missed` is terminal and never softens back to a warning. Takes the
        same arguments as `deadlines_for`, plus today's date, the warning window in
        days, and the date the plan answered if it has. Dates are ISO (YYYY-MM-DD)."""
        deadlines = clocks.compute(plan_type, service_type, notice_date, stage,
                                   internal_levels, grandfathered, filed_on)
        return clocks.risk(deadlines, today, warn_days, answered_on)
