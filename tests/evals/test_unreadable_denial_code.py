"""A denial code nobody has seen.

About a third of in-network denials are reported with no reason listed at all, so a
code this build cannot read is the ordinary case rather than the exotic one. The
question an eval has to settle is what the system does with it — and specifically
what it does when the unreadable code arrives *alongside* one it knows perfectly
well, which is the tempting case: read the half you can, draft against that, and
say nothing about the rest.

The half it cannot read might be the clinical half.
"""

from __future__ import annotations

from recourse.domain.codes import classify
from recourse.domain.evidence import can_prepare_alone, requirements_for
from recourse.domain.types import DenialClass
from tests.evals.support import seeded


def test_a_code_this_build_has_never_heard_of_is_unassessable_and_not_a_guess():
    """CARC ZQ4 does not exist. Nothing about it resembles anything in the table,
    and the answer is that it cannot be assessed rather than a nearest match."""
    found = classify(("ZQ4",))
    assert found.denial_class is DenialClass.UNASSESSABLE
    assert found.is_assessable is False
    assert found.unknown_codes == ("ZQ4",)
    assert "ZQ4" in found.reason and "not in the X12 table" in found.reason


def test_the_same_line_stays_unassessable_when_a_familiar_code_sits_beside_it():
    """CARC 16 is the most readable code there is — a billing error, the one class
    this agent can prepare on its own. Put ZQ4 next to it and the line is still
    unassessable. Drafting a clerical appeal here would answer one of the two things
    the insurer said and ignore the other."""
    alone = classify(("16",), ("N290",))
    assert alone.denial_class is DenialClass.CLERICAL

    together = classify(("16", "ZQ4"), ("N290",))
    assert together.denial_class is DenialClass.UNASSESSABLE
    assert together.unknown_codes == ("ZQ4",)


def test_an_unassessable_denial_gets_no_checklist_and_is_never_prepared_alone():
    """There is no document list for a reason nobody stated. Inventing one would
    dress a guess as a checklist and send a patient chasing paperwork that answers
    nothing."""
    _, case = seeded()
    assert requirements_for(DenialClass.UNASSESSABLE) == ()
    assert can_prepare_alone(case, DenialClass.UNASSESSABLE) is False


def test_but_the_recognised_half_is_dropped_from_the_answer_entirely():
    """Recorded because it was expected to survive, and it does not.

    On `("16", "ZQ4")` the classification comes back with `matched=None` and a
    reason naming only ZQ4. The engine did recognise CARC 16 — `classify(("16",))`
    proves it — and then discarded that on the way out. Failing closed is right;
    losing the half it could read means a person is told 'unreadable code ZQ4' when
    the more useful sentence is 'a billing error, plus something we cannot read'.
    """
    together = classify(("16", "ZQ4"))
    assert together.matched is None
    assert "16" not in together.reason
