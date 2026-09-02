"""The audit trail, the dial, and the reset.

`POST /api/demo/reset` rebuilds the state through `build_state`, the same function
start-up calls, so a reset console is the console a cold start produces. Muster's
reset built its state a second way and forgot the seeding its guards depended on,
which produced a console where every control was refused and nothing said why.

The autonomy level survives the reset on purpose: it is the operator's setting, not
part of the demo world, and silently returning someone's dial to the default between
two takes would be a change they did not ask for and would not see.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from recourse.api.state import RecourseState, build_state
from recourse.domain.types import AutonomyLevel
from recourse.policy.rules import NON_NEGOTIABLE_RULES, THRESHOLDS


class AutonomyIn(BaseModel):
    level: AutonomyLevel


def _autonomy_view(state: RecourseState) -> dict[str, Any]:
    limits = THRESHOLDS[state.autonomy]
    return {
        "level": state.autonomy.value,
        "levels": [level.value for level in AutonomyLevel],
        "thresholds": {
            "warn_days": limits.warn_days,
            "may_draft_unprompted": limits.may_draft_unprompted,
            "may_request_records": limits.may_request_records,
        },
        # Sent with every read of the dial, because the three rules beneath it are
        # the product's actual promise and a screen that only showed the dial would
        # imply the dial is all there is.
        "non_negotiable_rules": sorted(NON_NEGOTIABLE_RULES),
    }


def add_record_routes(app: FastAPI) -> None:
    @app.get("/api/timeline")
    def get_timeline() -> list[dict[str, Any]]:
        """Every model call and tool call, taken from the loop rather than the agent."""
        state: RecourseState = app.state.recourse
        return [
            {"kind": e.kind, "label": e.label, "at": e.at.isoformat(), "detail": e.detail}
            for e in state.trail.entries()
        ]

    @app.get("/api/autonomy")
    def get_autonomy() -> dict[str, Any]:
        return _autonomy_view(app.state.recourse)

    @app.put("/api/autonomy")
    def put_autonomy(payload: AutonomyIn) -> dict[str, Any]:
        state: RecourseState = app.state.recourse
        state.autonomy = payload.level
        return _autonomy_view(state)

    @app.post("/api/demo/reset")
    def reset_demo() -> dict[str, Any]:
        """Put the world back to how it started. See the module docstring."""
        state: RecourseState = app.state.recourse
        app.state.recourse = build_state(autonomy=state.autonomy)
        return {"status": "reset", "autonomy": app.state.recourse.autonomy.value}
