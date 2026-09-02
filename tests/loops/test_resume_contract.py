"""The resume contract: a decline never goes back to the agent.

Its own file because it is not about how a run is assembled. It is the guarantee that
cost the most elsewhere — in Muster an operator declined a change, the resumed run
performed it, and the receipt carried the name of the person who had refused it — and
the whole point here is that it is locked twice: the API does not call the resumer on
a decline, and the resumer refuses to be called.
"""

from __future__ import annotations

import pytest

from recourse.domain.types import DecisionOutcome
from recourse.loops.press import runner as press_runner
from recourse.loops.press.tools import PRESS_TOOLS
from recourse.loops.resume import loop_for, resume_decision
from recourse.loops.watch import runner as watch_runner
from recourse.loops.watch.tools import WATCH_TOOLS
from recourse.persistence.decisions import Decision, PendingDecision
from recourse.policy.escalation import GUARDED_TOOLS


def _pending(outcome: DecisionOutcome, tool: str = "draft_letter_body") -> PendingDecision:
    decision = Decision(decision_id="dec-1", rule="deadline_at_risk",
                        prompt="30 days remain. Approve this?")
    return PendingDecision(
        decision=decision.answer(outcome, by="Adaeze Okafor", role="self"),
        interrupt_id="v1:before_tool_call:tooluse_ABC:xyz",
        snapshot={}, proposal={"tool": tool, "denial_id": "den-16"},
    )


@pytest.mark.parametrize("resume", [watch_runner.resume_watch, press_runner.resume_press])
def test_resuming_is_documented_as_the_callers_job_on_an_approval_only(resume):
    """The contract is pinned as well as enforced: a rewrite that drops it fails."""
    assert "approval" in resume.__doc__ or "approved" in resume.__doc__


async def test_a_declined_decision_is_refused_before_any_agent_is_built():
    """The second lock. Nothing is constructed, nothing is invoked, nothing changes."""
    with pytest.raises(ValueError) as raised:
        await resume_decision(object(), _pending(DecisionOutcome.DECLINE))
    assert "never resumed" in str(raised.value)


async def test_an_unanswered_decision_is_refused_too():
    pending = _pending(DecisionOutcome.APPROVE)
    pending.decision = Decision(decision_id="dec-1", rule="r", prompt="p")
    with pytest.raises(ValueError):
        await resume_decision(object(), pending)


def test_the_stopped_call_says_which_loop_to_resume():
    assert loop_for({"tool": "draft_letter_body"}) == "watch"
    assert loop_for({"tool": "notify_person"}) == "press"


def test_a_decision_with_no_recognisable_tool_is_refused_rather_than_guessed():
    """Resuming the wrong loop would answer a question nobody asked."""
    with pytest.raises(LookupError):
        loop_for({"tool": "something_nobody_declared"})


def test_the_two_loops_guarded_tools_are_disjoint():
    """The premise of the dispatch above. If these ever overlap, it stops working."""
    watch_guarded = GUARDED_TOOLS & set(WATCH_TOOLS)
    press_guarded = GUARDED_TOOLS & set(PRESS_TOOLS)
    assert watch_guarded and press_guarded
    assert not (watch_guarded & press_guarded)
