"""What each loop hands the escalation policy, and what the policy does with it.

The context providers are where the model's arguments stop mattering. The agent says
which denial; the class, the clock and the days remaining are read from the record, so
an agent that understates a deadline in its argument is still judged on the real one.
"""

from __future__ import annotations

from strands.interventions.actions import Confirm, Proceed

from recourse.domain.types import AutonomyLevel
from recourse.loops.press.context import build_press_context_provider
from recourse.loops.watch.context import build_watch_context_provider
from recourse.policy.escalation import EscalationPolicy
from tests.loops.support import seeded
from tests.policy.support import tool_event

LEVEL = AutonomyLevel.BALANCED


def _watch_policy(prompted: bool = True) -> EscalationPolicy:
    world, store = seeded()
    return EscalationPolicy(LEVEL, build_watch_context_provider(store, world.now, LEVEL, prompted))


def _press_policy() -> EscalationPolicy:
    world, store = seeded()
    return EscalationPolicy(LEVEL, build_press_context_provider(store, world.now, LEVEL))


def _rules(policy: EscalationPolicy, event) -> list[str]:
    action = policy.before_tool_call(event)
    return [hit.rule for hit in policy.last_hits] if isinstance(action, Confirm) else []


def test_reading_the_case_file_is_never_escalated():
    """Three of the five WATCH tools commit nothing and reach nobody."""
    policy = _watch_policy()
    for name in ("list_denials", "explain_denial", "check_evidence"):
        assert isinstance(policy.before_tool_call(tool_event(name, denial_id="den-16")), Proceed)


def test_a_draft_against_a_closing_window_is_not_stopped():
    """Day 150 of 180 on the clinical appeal. The rule fires *because* it must act."""
    policy = _watch_policy()
    assert "deadline_at_risk" not in _rules(policy, tool_event("draft_letter_body",
                                                           denial_id="den-50"))


def test_asking_a_provider_for_records_needs_a_person_at_this_level():
    policy = _watch_policy()
    rules = _rules(policy, tool_event("request_document", denial_id="den-197",
                                      kind="authorization", from_whom="Meridian"))
    assert "records_request_needs_you" in rules


def test_a_denial_the_provider_cannot_read_escalates_rather_than_proceeding():
    """Unknown is never benign. `None` from the provider means unassessable."""
    policy = _watch_policy()
    assert _rules(policy, tool_event("draft_letter_body", denial_id="den-nope")) \
        == ["unassessable"]


def test_the_policy_is_never_asked_to_approve_an_uncited_clinical_sentence():
    """`CitationGuard` denies it first, and a Deny is not a question.

    The provider therefore leaves `uncited_clinical` empty on purpose: filling it in
    would turn that refusal into a Confirm, and there is nothing for somebody
    mid-triage to approve about a statement the record does not support.
    """
    world, store = seeded()
    provide = build_watch_context_provider(store, world.now, LEVEL, prompted=True)
    context = provide("draft_letter_body", {"denial_id": "den-50"})
    assert context is not None and context.uncited_clinical == ()


def test_a_silent_insurer_does_not_stop_the_run_either():
    """19 days past its own 60. Nobody but the claimant is counting that one."""
    policy = _press_policy()
    assert "insurer_overdue" not in _rules(policy, tool_event("notify_person",
                                                          appeal_id="appeal-16"))


def test_an_appeal_that_is_on_track_is_not_escalated():
    """A loop that stopped on everything would be a loop nobody left switched on."""
    policy = _press_policy()
    assert _rules(policy, tool_event("notify_person", appeal_id="appeal-197")) == []
