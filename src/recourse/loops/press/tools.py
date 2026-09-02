"""The PRESS agent's tool set: five tools, and there is no sixth.

Two read (`reading.py`) and three change something (`writing.py`).

**There is deliberately no tool that files an appeal**, and none that marks one filed.
This is the loop that would want one — it is the loop that watches a deadline close —
and that is exactly why the capability does not exist here. Filing is a legal act
taken in the patient's name; the agent prepares and presses, and a person sends. A
test asserts this list, so a filing tool added later fails the suite.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from recourse.domain.types import AutonomyLevel
from recourse.loops.press.board import Board
from recourse.loops.press.reading import build_reading_tools
from recourse.loops.press.writing import build_writing_tools
from recourse.persistence.store import CaseStore

PRESS_TOOLS: tuple[str, ...] = (
    "open_appeals", "sweep_deadlines", "record_response", "advance_stage", "notify_person",
)


def build_press_tools(
    store: CaseStore,
    clock: Callable[[], date],
    level: AutonomyLevel = AutonomyLevel.BALANCED,
    notices: list[dict[str, Any]] | None = None,
    board: Board | None = None,
) -> list[Any]:
    """The five tools, closed over one case file, one clock and one board.

    `board` is accepted so a caller can hold the same cache the tools read — the
    resumed-run case, where a new closure would otherwise start blind.
    """
    board = Board(store, clock, level) if board is None else board
    return [
        *build_reading_tools(store, board),
        *build_writing_tools(store, board, [] if notices is None else notices),
    ]
