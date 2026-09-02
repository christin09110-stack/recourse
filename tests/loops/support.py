"""Shared fixtures for the loop tests.

Offline throughout. Nothing here reaches Bedrock, and nothing needs credentials: the
tools are plain callables closed over a seeded world, so the whole tool layer can be
driven without a model in the loop. The model's judgement is not what these tests are
about — what the tools refuse, and what they refuse to make up, is.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from recourse.adapters.simulated import SimulatedWorld
from recourse.domain.types import AutonomyLevel
from recourse.loops.press.tools import build_press_tools
from recourse.loops.watch.tools import build_watch_tools
from recourse.persistence.store import CaseStore


def seeded(today: date | None = None) -> tuple[SimulatedWorld, CaseStore]:
    world = SimulatedWorld(today)
    return world, CaseStore(world.case_file())


def watch(today: date | None = None) -> tuple[CaseStore, dict[str, Any], list[dict[str, Any]]]:
    """The WATCH tools by name, plus the request list they append to."""
    world, store = seeded(today)
    requests: list[dict[str, Any]] = []
    tools = {t.tool_name: t for t in build_watch_tools(store, world.now, requests)}
    return store, tools, requests


def press(
    today: date | None = None, level: AutonomyLevel = AutonomyLevel.BALANCED,
) -> tuple[CaseStore, dict[str, Any], list[dict[str, Any]]]:
    """The PRESS tools by name, plus the notice list they append to."""
    world, store = seeded(today)
    notices: list[dict[str, Any]] = []
    tools = {t.tool_name: t for t in build_press_tools(store, world.now, level, notices)}
    return store, tools, notices
