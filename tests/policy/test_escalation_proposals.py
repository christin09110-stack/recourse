"""What the policy remembers about the call it stopped, and the ordering above it."""

from types import SimpleNamespace

from strands.interventions.actions import Deny, Proceed

from recourse.domain.types import AutonomyLevel
from recourse.policy import escalation
from recourse.policy.escalation import (
    EscalationPolicy, proposal_that_paused, rules_that_paused,
)
from recourse.policy.rules import RuleHit
from tests.policy.support import case_with, guard_over, said, tool_event

_AT_RISK = [RuleHit("deadline_at_risk", "This appeal is 150 days into its 180.")]


def _policy(monkeypatch, *hit_lists):
    answers = iter(hit_lists)
    monkeypatch.setattr(escalation, "evaluate", lambda context, lvl: next(answers))
    return EscalationPolicy(AutonomyLevel.CONSERVATIVE, lambda name, args: object())


def _result(tool_use_id):
    return SimpleNamespace(
        interrupts=[SimpleNamespace(id=f"v1:before_tool_call:{tool_use_id}:b174861a")],
    )


def test_the_policy_records_the_call_it_stopped_not_only_the_reason(monkeypatch):
    """So the question put to the person names the denial it is about."""
    policy = _policy(monkeypatch, _AT_RISK)
    policy.before_tool_call(
        tool_event("notify_person", "tu-9", appeal_id="ap-3", denial_id="dn-3"))

    proposal = proposal_that_paused(_result("tu-9"), policy)
    assert proposal["tool"] == "notify_person"
    assert proposal["appeal_id"] == "ap-3"


def test_a_run_that_cleared_one_guard_and_paused_on_another_reports_the_second(monkeypatch):
    """`last_hits` would by then describe the wrong call, and so would its arguments."""
    policy = _policy(monkeypatch, [], _AT_RISK)
    policy.before_tool_call(tool_event("draft_letter_body", "tu-1", appeal_id="ap-1"))
    policy.before_tool_call(tool_event("advance_stage", "tu-2", appeal_id="ap-2"))

    result = _result("tu-2")
    assert proposal_that_paused(result, policy)["appeal_id"] == "ap-2"
    assert [h.rule for h in rules_that_paused(result, policy)] == ["deadline_at_risk"]


def test_a_result_with_no_interrupts_falls_back_to_the_last_hits(monkeypatch):
    policy = _policy(monkeypatch, _AT_RISK)
    policy.before_tool_call(tool_event("advance_stage", "tu-4"))
    assert rules_that_paused(SimpleNamespace(interrupts=None), policy) == policy.last_hits


def test_the_citation_guard_runs_first_and_its_deny_short_circuits(monkeypatch):
    """Ordering is the enforcement.

    The escalation policy weighs a call on deadlines and autonomy level, none of
    which has an opinion about whether a sentence is true. Reached second, it would
    have let this packet through.
    """
    guard, policy = guard_over(case_with()), _policy(monkeypatch, [])
    call = tool_event("draft_letter_body", assertions=[said("The infusion was necessary.")])

    assert isinstance(guard.before_tool_call(call), Deny)
    # And the policy that would have been asked next finds nothing wrong with it.
    assert isinstance(policy.before_tool_call(call), Proceed)


def test_a_short_tool_use_id_does_not_claim_a_longer_ones_interrupt(monkeypatch):
    """"tu-1" is a substring of "tu-10", and containment alone would let the first
    registered pause answer for the second."""
    policy = _policy(monkeypatch, _AT_RISK, _AT_RISK)
    policy.before_tool_call(tool_event("advance_stage", "tu-1", appeal_id="ap-1"))
    policy.before_tool_call(tool_event("advance_stage", "tu-10", appeal_id="ap-10"))

    assert proposal_that_paused(_result("tu-10"), policy)["appeal_id"] == "ap-10"
