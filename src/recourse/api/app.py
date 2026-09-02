"""Recourse's control plane: the FastAPI surface the console and the demo talk to.

The state lives on `app.state.recourse`, one process-wide `RecourseState` built by
`build_state` — the same function `POST /api/demo/reset` calls, so a reset console is
the console a cold start produces.

`watch_runner`, `press_runner` and `decision_resumer` are injected rather than
imported, so the tests can swap the Strands agents for fakes without touching a
network or an AWS credential. `create_app()` with no arguments wires the real loops,
lazily, in `runners.py`.

The property this module exists to hold: **answering a decision with a decline
resumes nothing.** It is recorded, the journal names who refused, and the run ends
in our own code. See `routes_decisions.py` for what happened when that was left to
the SDK's own callback.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from recourse.api.routes_case import add_case_routes
from recourse.api.routes_clocks import add_clock_routes
from recourse.api.routes_decisions import add_decision_routes
from recourse.api.routes_eob import add_eob_routes
from recourse.api.routes_journal import add_journal_routes
from recourse.api.routes_loops import add_loop_routes
from recourse.api.routes_record import add_record_routes
from recourse.api.runners import (
    default_decision_resumer,
    default_press_runner,
    default_watch_runner,
)
from recourse.api.state import build_state


def create_app(
    *,
    watch_runner: Any = None,
    press_runner: Any = None,
    decision_resumer: Any = None,
) -> FastAPI:
    """The whole API. Every argument defaults to the real loop, wired lazily."""
    app = FastAPI(title="Recourse")
    app.state.recourse = build_state()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    add_case_routes(app)
    add_clock_routes(app)
    add_eob_routes(app)
    add_loop_routes(app, watch_runner or default_watch_runner,
                    press_runner or default_press_runner)
    add_decision_routes(app, decision_resumer or default_decision_resumer)
    add_journal_routes(app)
    add_record_routes(app)

    # Mounted last and at "/", so it can never shadow an API path. A static mount
    # answers 405 rather than 404 for a path it does not have, which is how Muster
    # shipped a console asking for /api/api/demo/reset and got a method error back
    # instead of "no such route" — see tests/api/test_console_routes.py.
    console_dir = os.environ.get("RECOURSE_CONSOLE_DIR")
    if console_dir and Path(console_dir).is_dir():
        app.mount("/", StaticFiles(directory=console_dir, html=True), name="console")

    return app


def main() -> None:
    """`recourse-api`. Host and port come from the environment for App Runner."""
    import uvicorn

    uvicorn.run(
        create_app(),
        host=os.environ.get("RECOURSE_HOST", "0.0.0.0"),  # noqa: S104 - container
        port=int(os.environ.get("PORT", "8080")),
    )
