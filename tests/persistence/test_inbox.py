import pytest

from recourse.domain.types import DecisionOutcome
from recourse.persistence.decisions import Decision
from recourse.persistence.inbox import DecisionInbox


def _decision(decision_id: str = "dec-1") -> Decision:
    return Decision(
        decision_id=decision_id, rule="deadline_at_risk", appeal_id="app-1",
        prompt="30 days left to file. Send the drafted appeal?",
    )


def _opened() -> DecisionInbox:
    inbox = DecisionInbox()
    inbox.open(_decision(), interrupt_id="int-1", snapshot={"scope": "agent"}, rule_hits=[])
    return inbox


def test_an_opened_decision_is_pending_with_its_snapshot():
    inbox = _opened()
    assert inbox.get("dec-1").interrupt_id == "int-1"
    assert inbox.get("dec-1").snapshot == {"scope": "agent"}
    assert inbox.get("dec-1").severity == 1


def test_the_snapshot_is_copied_so_a_later_mutation_cannot_corrupt_it():
    inbox = DecisionInbox()
    snapshot = {"scope": "agent"}
    inbox.open(_decision(), interrupt_id="int-1", snapshot=snapshot, rule_hits=[])
    snapshot["scope"] = "tampered"
    assert inbox.get("dec-1").snapshot == {"scope": "agent"}


def test_reopening_a_pending_id_raises_rather_than_discarding_the_snapshot():
    inbox = _opened()
    with pytest.raises(KeyError, match="already pending"):
        inbox.open(_decision(), interrupt_id="int-2", snapshot={}, rule_hits=[])
    assert inbox.get("dec-1").interrupt_id == "int-1"


def test_answering_records_the_outcome_the_person_the_role_and_the_note():
    inbox = _opened()
    answered = inbox.answer(
        "dec-1", DecisionOutcome.APPROVE, by="Ana Okafor", role="member",
        note="Posted it myself on the 14th.",
    )
    assert answered.decision.outcome is DecisionOutcome.APPROVE
    assert answered.decision.by == "Ana Okafor"
    assert answered.decision.role == "member"
    assert answered.decision.note == "Posted it myself on the 14th."
    assert answered.decision.at is not None
    assert inbox.pending() == []
    assert len(inbox.answered()) == 1


def test_answering_an_unknown_decision_raises():
    with pytest.raises(KeyError, match="nope"):
        DecisionInbox().answer("nope", DecisionOutcome.APPROVE, by="a", role="b")


def test_raising_severity_makes_it_louder_and_leaves_it_open():
    # A deadline escalation nobody has answered must get louder, never quieter:
    # silence as a filing window closes is the one unrecoverable outcome here.
    inbox = _opened()
    inbox.raise_severity("dec-1")
    assert inbox.raise_severity("dec-1").severity == 3
    assert [p.decision.decision_id for p in inbox.pending()] == ["dec-1"]
    assert inbox.answered() == []


def test_raising_severity_on_an_answered_decision_raises():
    inbox = _opened()
    inbox.answer("dec-1", DecisionOutcome.DECLINE, by="Ana Okafor", role="member")
    with pytest.raises(KeyError, match="no pending decision"):
        inbox.raise_severity("dec-1")
