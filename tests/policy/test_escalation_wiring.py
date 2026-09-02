"""The one place the handler is run against the real rule engine.

Everything else in `test_escalation.py` stubs `evaluate`, which keeps a threshold
change from breaking tests about tool-use bookkeeping — and would also let the two
drift apart unnoticed if nothing ever joined them up.
"""

from strands.interventions.actions import Confirm, Proceed

from recourse.domain.types import AutonomyLevel, DeadlineRisk
from recourse.policy.escalation import EscalationPolicy
from recourse.policy.rules import NON_NEGOTIABLE_RULES, ActionContext
from tests.policy.support import tool_event


def _policy(level, **context):
    return EscalationPolicy(
        level, lambda name, args: ActionContext(tool=name, **context))


def test_a_settled_case_at_trusted_proceeds():
    policy = _policy(AutonomyLevel.TRUSTED)
    assert isinstance(policy.before_tool_call(tool_event("advance_stage")), Proceed)


def test_a_closing_deadline_stops_the_run_even_at_trusted():
    """`deadline_at_risk` is a duty, not a threshold: no level reaches it."""
    policy = _policy(AutonomyLevel.TRUSTED, risk=DeadlineRisk.CRITICAL, days_remaining=5)
    action = policy.before_tool_call(tool_event("advance_stage"))
    assert isinstance(action, Confirm)
    assert action.reason in NON_NEGOTIABLE_RULES
