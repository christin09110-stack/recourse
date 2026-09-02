"""The tool sets are exactly what was declared, and neither of them can file.

This is the test that fails if somebody adds a filing tool. Rule 2 — the agent never
files — is enforced by the absence of the capability rather than by a guard, and an
absence needs a test or it is only a habit.
"""

from __future__ import annotations

from recourse.loops.press.tools import PRESS_TOOLS
from recourse.loops.watch.tools import WATCH_TOOLS
from tests.loops.support import press, watch

#: Any name shaped like submitting rather than preparing. Substring matching on
#: purpose: `file_appeal`, `submit_to_insurer` and `send_letter` must all trip it.
_FILING_WORDS = ("file", "submit", "send", "post", "mail", "transmit", "lodge")


def test_the_watch_loop_has_exactly_its_five_tools():
    _, tools, _ = watch()
    assert sorted(tools) == sorted(WATCH_TOOLS)
    assert sorted(WATCH_TOOLS) == [
        "check_evidence", "draft_letter_body", "explain_denial",
        "list_denials", "request_document",
    ]


def test_the_press_loop_has_exactly_its_five_tools():
    _, tools, _ = press()
    assert sorted(tools) == sorted(PRESS_TOOLS)
    assert sorted(PRESS_TOOLS) == [
        "advance_stage", "notify_person", "open_appeals",
        "record_response", "sweep_deadlines",
    ]


def test_no_tool_in_either_loop_files_anything():
    """Filing is a legal act taken in the patient's name. Nothing here may do it."""
    _, watch_tools, _ = watch()
    _, press_tools, _ = press()
    for name in (*watch_tools, *press_tools):
        assert not any(word in name for word in _FILING_WORDS), (
            f"{name!r} is shaped like filing. Recourse prepares and a person sends; "
            "if this tool really does not file, it needs a name that says so."
        )


def test_a_drafted_letter_is_not_a_sent_one():
    """The one place a draft could quietly become a filing is the appeal it lands on."""
    store, tools, _ = watch()
    before = store.appeal("appeal-16").sent_on
    drafted = tools["draft_letter_body"](
        denial_id="den-16",
        assertions=[{"text": "The claim omitted the rendering provider identifier.",
                     "clinical": False}],
    )
    assert drafted["sent"] is False
    # Redrafting does not touch when — or whether — a person posted it. `mark_sent`
    # is the only thing that moves this field, and no tool in either loop calls it.
    assert store.appeal(drafted["appeal_id"]).sent_on == before
