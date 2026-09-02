"""Wiring the real agent loops in, without importing them to start up.

The loops are imported *inside* these functions, never at module scope. Two reasons,
and the second is the one that bites: an import-time dependency on `recourse.loops`
would mean an API that cannot be tested, or even imported, unless a Bedrock-shaped
agent module is present and healthy — and every test in `tests/api/` injects fakes
precisely so it can run with no credentials and no network.

A loop that is not wired up yet fails here, as a 503 that names the entry point it
looked for. That is a great deal more use than an ImportError at start-up, which
takes down the health check, the case file and the deadline screen along with it.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from fastapi import HTTPException

#: kind -> (module, callable). The loops own their own wiring; this only calls it.
_ENTRY_POINTS: dict[str, tuple[str, str]] = {
    "watch": ("recourse.loops.watch.runner", "run_watch"),
    "press": ("recourse.loops.press.runner", "run_press"),
    "resume": ("recourse.loops.resume", "resume_decision"),
}


def _entry(kind: str) -> Any:
    module_name, attr = _ENTRY_POINTS[kind]
    try:
        return getattr(import_module(module_name), attr)
    except (ImportError, AttributeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(f"the {kind.upper()} loop is not wired up: expected "
                    f"{module_name}.{attr}, and it is not importable ({exc})"),
        ) from exc


async def default_watch_runner(state: Any) -> Any:
    """Triage the case file with the real WATCH agent."""
    return await _entry("watch")(state)


async def default_press_runner(state: Any) -> Any:
    """Sweep every open appeal's clocks with the real PRESS agent."""
    return await _entry("press")(state)


async def default_decision_resumer(state: Any, pending: Any) -> Any:
    """Resume the paused run a person has just approved.

    Only ever called for an approval. A decline is enforced in `routes_decisions`
    and never reaches an agent at all — see that module's docstring.
    """
    return await _entry("resume")(state, pending)
