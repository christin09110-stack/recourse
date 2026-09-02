"""Appeals and deadlines — the screen that carries the product.

`GET /api/deadlines` is `policy.sweep.sweep` and nothing else: the same pure function
the PRESS loop runs, ordered worst first by the same table. A second ordering here
would be a second opinion about which clock matters most, and the one that buried a
missed window under three warnings would be sorting by tidiness.

The warning window comes from the autonomy dial, because how early to speak is the
one thing about a deadline the dial is allowed to move. It never moves whether to
speak: `deadline_at_risk` fires at every level.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from recourse.api.clocks_view import finding_view
from recourse.api.state import RecourseState
from recourse.api.views import appeal_view
from recourse.policy.rules import THRESHOLDS
from recourse.policy.sweep import sweep


def add_clock_routes(app: FastAPI) -> None:
    @app.get("/api/appeals")
    def get_appeals() -> list[dict[str, Any]]:
        """Every appeal, its levels, its history and both of its clocks."""
        state: RecourseState = app.state.recourse
        warn_days = THRESHOLDS[state.autonomy].warn_days
        now = state.world.now()
        return [
            appeal_view(state.case, appeal, now, warn_days)
            for appeal in state.case.appeals.values()
        ]

    @app.get("/api/deadlines")
    def get_deadlines() -> list[dict[str, Any]]:
        """Every open appeal that needs saying out loud, worst first."""
        state: RecourseState = app.state.recourse
        findings = sweep(state.case, state.world.now(), state.autonomy)
        return [finding_view(state.case, finding) for finding in findings]
