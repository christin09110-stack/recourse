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


def test_a_closing_deadline_does_not_stop_the_run():
    """`deadline_at_risk` is a duty to speak, discharged by `policy.sweep` on a
    schedule — not a threshold on a tool call. Judged here it became a rule against
    acting, and the first live run held the agent back from drafting a letter for
    the appeal whose insurer was already nineteen days late."""
    policy = _policy(AutonomyLevel.TRUSTED, risk=DeadlineRisk.CRITICAL, days_remaining=5)
    assert isinstance(policy.before_tool_call(tool_event("advance_stage")), Proceed)
