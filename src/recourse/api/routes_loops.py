"""Starting the two loops from the console.

`POST /api/triage` runs WATCH over the case file: classify what arrived, check what
the file already holds, draft what the evidence supports. `POST /api/press` runs the
deadline duty over every open appeal.

Both come back one of two ways — finished, or parked on a question. There is no
third answer, and in particular there is no "started, check back later": a run that
paused and told nobody is the silence this product exists to break.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from recourse.api.parking import open_decision
from recourse.api.state import RecourseState


def _answer(state: RecourseState, result: Any, done: str) -> dict[str, Any]:
    """Either the run finished, or it is now a question waiting for a person."""
    if getattr(result, "paused", False):
        return {"status": "awaiting_decision", "decision_id": open_decision(state, result)}
    return {"status": done, "text": getattr(result, "text", "")}


def add_loop_routes(app: FastAPI, watch_runner: Any, press_runner: Any) -> None:
    @app.post("/api/triage")
    async def post_triage() -> dict[str, Any]:
        """Run WATCH over the case file: classify, check evidence, draft."""
        state: RecourseState = app.state.recourse
        state.journal.write(
            kind="triage_started",
            sentence="Recourse began triaging the denials in this case file.",
            at=state.world.now_at(),
        )
        return _answer(state, await watch_runner(state), "triaged")

    @app.post("/api/press")
    async def post_press() -> dict[str, Any]:
        """Run PRESS: sweep every open appeal's clocks and raise what is at risk."""
        state: RecourseState = app.state.recourse
        return _answer(state, await press_runner(state), "swept")
