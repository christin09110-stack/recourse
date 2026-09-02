"""The clocks over MCP: the same arithmetic, and the same refusals.

There is no world behind this protocol, so the caller states the facts and gets dates
back. What does not travel is a guess: a plan type with no clock table is an error
over the wire exactly as it is in process, because a non-health ERISA plan allows 60
days rather than 180 and the generous answer is the one that loses the appeal.
"""

from __future__ import annotations

import pytest

from recourse.mcp_server.server import build_server

from .conftest import payload as _payload


async def test_deadlines_over_mcp_are_the_regulations_own_arithmetic():
    payload = _payload(await build_server().call_tool("deadlines_for", {
        "plan_type": "aca_marketplace", "service_type": "post_service",
        "notice_date": "2026-03-04",
    }))
    assert payload["my_deadline"] == "2026-08-31"  # 180 days
    # Not filed, so the plan's clock has not started. A null is "not yet", never
    # "expired", and never a date invented to fill the field.
    assert payload["their_deadline"] is None
    assert payload["citation"].startswith("https://")


async def test_a_two_level_erisa_appeal_splits_the_plans_clock():
    args = {"plan_type": "erisa_group_health", "service_type": "post_service",
            "notice_date": "2026-03-04", "filed_on": "2026-03-10"}
    one = _payload(await build_server().call_tool("deadlines_for", {**args, "internal_levels": 1}))
    two = _payload(await build_server().call_tool("deadlines_for", {**args, "internal_levels": 2}))
    assert one["their_deadline"] == "2026-05-09"   # 60 days, one level
    assert two["their_deadline"] == "2026-04-09"   # 30, and then 30 more


async def test_check_risk_reports_a_missed_window_as_missed():
    payload = _payload(await build_server().call_tool("check_risk", {
        "plan_type": "aca_marketplace", "service_type": "post_service",
        "notice_date": "2025-01-01", "today": "2026-09-02",
    }))
    assert payload["risk"] == "missed"
    assert payload["days_remaining"] < 0


async def test_a_plan_type_with_no_clock_table_is_refused_not_defaulted():
    with pytest.raises(Exception, match="out of scope"):
        await build_server().call_tool("plan_rules", {"plan_type": "erisa_non_health"})
