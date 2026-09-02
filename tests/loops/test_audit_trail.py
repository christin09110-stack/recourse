"""The trail is written by hooks on the loop, not by the agent describing itself.

The record is what a person, an ombudsman or a court reads afterwards. An agent's own
account of what it did is the one thing that cannot be trusted when the record is the
defence, so these tests check that the trail comes from the loop's events.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from strands.hooks.events import AfterToolCallEvent, BeforeModelCallEvent, BeforeToolCallEvent

from recourse.hooks.audit import AuditTrail


class _Registry:
    """Enough of a HookRegistry to see what got registered against what."""

    def __init__(self) -> None:
        self.callbacks: dict[Any, Any] = {}

    def add_callback(self, event_type: Any, callback: Any) -> None:
        self.callbacks[event_type] = callback


def _registered() -> tuple[AuditTrail, dict[Any, Any]]:
    trail, registry = AuditTrail(), _Registry()
    trail.register_hooks(registry)
    return trail, registry.callbacks


def test_it_registers_against_the_three_events_that_make_up_the_record():
    _, callbacks = _registered()
    assert set(callbacks) == {BeforeModelCallEvent, BeforeToolCallEvent, AfterToolCallEvent}


def test_a_tool_call_and_its_result_both_reach_the_trail():
    trail, callbacks = _registered()
    event = SimpleNamespace(tool_use={"name": "draft_letter_body",
                                      "input": {"denial_id": "den-16"}})
    callbacks[BeforeToolCallEvent](event)
    callbacks[AfterToolCallEvent](event)

    call, result = trail.entries()
    assert (call.kind, call.label) == ("tool_call", "draft_letter_body")
    # The arguments, not a summary. "drafted a letter" is not a record; which denial is.
    assert call.detail == {"denial_id": "den-16"}
    assert (result.kind, result.label) == ("tool_result", "draft_letter_body")


def test_arguments_are_copied_so_a_later_mutation_cannot_rewrite_history():
    trail, callbacks = _registered()
    args = {"denial_id": "den-16"}
    callbacks[BeforeToolCallEvent](SimpleNamespace(tool_use={"name": "x", "input": args}))
    args["denial_id"] = "den-50"
    assert trail.entries()[0].detail == {"denial_id": "den-16"}


def test_the_caller_cannot_edit_the_record_through_the_list_it_gets_back():
    trail, _ = _registered()
    trail.record("refusal", "uncited_clinical_assertion")
    trail.entries().clear()
    assert len(trail.entries()) == 1


def test_a_refusal_that_never_reached_a_tool_can_still_be_written_down():
    """A `Deny` leaves no BeforeToolCallEvent behind it, and a refusal missing from
    the log reads as a thing that never happened."""
    trail, _ = _registered()
    trail.record("refusal", "uncited_clinical_assertion", {"denial_id": "den-50"})
    assert trail.of_kind("refusal")[0].detail == {"denial_id": "den-50"}
