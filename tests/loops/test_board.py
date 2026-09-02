"""The per-run cache, and the resumed run that arrives with an empty one.

This is Muster's most expensive bug, transposed. A resumed run is a *new* agent with
a *new* tools closure, so a cache the previous instance filled is gone — and the
operator has just approved acting on something that instance surfaced. Muster refused
it as unknown, the model tried something else, that escalated too, and approving a
decision produced a fresh copy of the same question.
"""

from __future__ import annotations

from recourse.domain.types import AutonomyLevel
from recourse.loops.press.board import Board
from recourse.loops.press.tools import build_press_tools
from tests.loops.support import press, seeded


def test_a_fresh_closure_re_derives_its_board_rather_than_refusing():
    """`notify_person` with no prior sweep — exactly the resumed run's position."""
    _, tools, notices = press()
    sent = tools["notify_person"](appeal_id="appeal-50", message="Any word yet?")
    assert sent["notified"] is True
    assert notices[0]["risk"] == "approaching"


def test_re_deriving_still_refuses_an_appeal_id_the_model_invented():
    """Re-deriving must not become "trust whatever was passed"."""
    _, tools, notices = press()
    assert "error" in tools["notify_person"](appeal_id="appeal-nope", message="hello")
    assert notices == []


def test_a_second_run_can_be_handed_the_board_the_first_one_filled():
    world, store = seeded()
    board = Board(store, world.now, AutonomyLevel.BALANCED)
    first = {t.tool_name: t for t in build_press_tools(store, world.now, board=board)}
    first["sweep_deadlines"]()

    second = {t.tool_name: t for t in
              build_press_tools(store, world.now, board=board)}
    assert second["notify_person"](appeal_id="appeal-16", message="chasing")["risk"] == "ok"


def test_the_board_reads_the_clocks_fresh_after_an_answer_moves_the_appeal():
    """A cached row would still describe the stage the appeal has just left."""
    world, store = seeded()
    board = Board(store, world.now, AutonomyLevel.BALANCED)
    board.sweep()
    tools = {t.tool_name: t for t in build_press_tools(store, world.now, board=board)}
    tools["record_response"](appeal_id="appeal-197", outcome="upheld",
                             answered_on="2026-09-01")
    tools["advance_stage"](appeal_id="appeal-197")
    assert board.clocks_on("appeal-197").stage.value == "internal_2"
