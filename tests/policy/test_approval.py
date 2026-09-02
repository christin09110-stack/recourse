from recourse.policy.approval import approves


def test_a_structured_decision_record_counts_as_approval():
    """Strands' default evaluator accepts only True or "yes".

    Recourse answers with a record — outcome, who decided, their relationship to the
    patient, their note — because all four end up on the receipt. In Muster, which
    answers the same way, that record read as "not approved": the operator pressed
    Approve, the run resumed, the same call was refused again, and the policy asked
    an identical question. Approving cloned the question it was answering.
    """
    assert approves({"outcome": "approve", "by": "Ana Okafor", "role": "member"}) is True
    assert approves({"decision": "yes", "by": "Ana Okafor"}) is True
    assert approves({"decision": "APPROVE "}) is True
    assert approves(True) is True
    assert approves("approve") is True
    assert approves("yes") is True


def test_anything_that_is_not_plainly_a_yes_is_a_no():
    assert approves({"outcome": "decline"}) is False
    assert approves({"decision": "decline", "by": "Ana Okafor"}) is False
    assert approves({}) is False
    assert approves({"by": "Ana Okafor"}) is False        # no outcome is not approval
    assert approves({"approved": "yes"}) is False      # unrecognised shape is a no
    assert approves(None) is False
    assert approves("no") is False
    assert approves(1) is False                        # truthiness is not consent
