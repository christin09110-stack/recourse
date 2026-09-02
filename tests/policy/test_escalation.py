"""The autonomy boundary.

`evaluate` is monkeypatched throughout. What each rule fires on belongs to
`test_rules.py`; what this handler does with a hit is the subject here, and coupling
the two would make a threshold change break tests about tool-use bookkeeping.
"""

from strands.interventions.actions import Confirm, Proceed

from recourse.domain.types import AutonomyLevel
from recourse.policy import escalation
from recourse.policy.approval import approves
from recourse.policy.escalation import GUARDED_TOOLS, EscalationPolicy
from recourse.policy.rules import RuleHit
from tests.policy.support import tool_event

_CONTEXT = object()  # The provider is injected; the handler never looks inside it.

_AT_RISK = [RuleHit("deadline_at_risk", "This appeal is 150 days into its 180.")]


def _policy(monkeypatch, *hit_lists, level=AutonomyLevel.BALANCED, provider=None):
    """A policy whose rule engine returns each of `hit_lists` in turn."""
    answers = iter(hit_lists)
    monkeypatch.setattr(escalation, "evaluate", lambda context, lvl: next(answers))
    return EscalationPolicy(level, provider or (lambda name, args: _CONTEXT))


def test_an_unguarded_tool_always_proceeds(monkeypatch):
    policy = _policy(monkeypatch)  # No hit list: evaluate must not be reached at all.
    assert isinstance(policy.before_tool_call(tool_event("list_denials")), Proceed)


def test_the_guarded_tools_are_the_ones_that_reach_a_person_or_commit_something():
    assert GUARDED_TOOLS == frozenset({
        "draft_letter_body", "mark_ready_to_send", "request_document",
        "notify_person", "record_response", "advance_stage",
    })


def test_no_tool_files_an_appeal():
    """Filing is a legal act in the patient's name. The capability does not exist,
    which is stronger than a guard: no approval and no autonomy level restores it."""
    assert not [t for t in GUARDED_TOOLS if "file" in t or "submit" in t or "send_to" in t]


def test_a_call_that_trips_nothing_proceeds(monkeypatch):
    policy = _policy(monkeypatch, [])
    assert isinstance(policy.before_tool_call(tool_event("draft_letter_body")), Proceed)


def test_a_rule_hit_confirms_and_carries_the_rule_in_plain_english(monkeypatch):
    policy = _policy(monkeypatch, _AT_RISK)
    action = policy.before_tool_call(tool_event("notify_person"))
    assert isinstance(action, Confirm)
    assert "150 days into its 180" in action.prompt
    assert action.reason == "deadline_at_risk"
    assert [h.rule for h in policy.last_hits] == ["deadline_at_risk"]


def test_the_confirm_carries_our_evaluator_not_the_sdk_default(monkeypatch):
    policy = _policy(monkeypatch, _AT_RISK)
    action = policy.before_tool_call(tool_event("advance_stage"))
    assert action.evaluate is approves


def test_a_context_the_provider_cannot_build_confirms_rather_than_proceeding(monkeypatch):
    """Unknown is never benign: an unreadable code is not "no action needed"."""
    policy = _policy(monkeypatch, level=AutonomyLevel.TRUSTED,
                     provider=lambda name, args: None)
    action = policy.before_tool_call(tool_event("record_response"))
    assert isinstance(action, Confirm)
    assert policy.last_hits[0].rule == "unassessable"


def test_a_clean_call_clears_the_last_hits(monkeypatch):
    policy = _policy(monkeypatch, _AT_RISK, [])
    policy.before_tool_call(tool_event("draft_letter_body"))
    policy.before_tool_call(tool_event("draft_letter_body"))
    assert policy.last_hits == []


def test_hits_are_kept_per_tool_use_so_a_later_call_cannot_overwrite_the_pause(monkeypatch):
    policy = _policy(monkeypatch, _AT_RISK)
    policy.before_tool_call(tool_event("notify_person", "tu-7"))
    assert policy.escalations["tu-7"][0].rule == "deadline_at_risk"


def test_before_tool_call_is_defined_on_the_class_not_the_instance():
    """Strands inspects the class; an instance attribute silently disables the guard."""
    assert "before_tool_call" in EscalationPolicy.__dict__
