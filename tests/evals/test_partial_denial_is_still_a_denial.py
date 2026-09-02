"""A partial denial is still a denial.

The second real defect, and the one that would never have shown up in a demo. The
test for "was this refused?" was "did the plan pay nothing?", which is true of every
denial anybody thinks of and false of a whole class nobody does: the plan pays eight
of the twelve physiotherapy visits and refuses four under an annual limit. Money
moved. The line looked paid. The four refused visits were invisible, and the person
who owed for them was never told they could contest it.

`line-physio-visits` is that line, seeded on purpose. $2,160 allowed, $1,440 paid,
$720 refused under CARC 96.
"""

from __future__ import annotations

from recourse.domain.money import Money
from recourse.domain.types import DenialClass
from tests.evals.support import seeded


def test_the_plan_paid_most_of_this_line_and_it_is_still_a_denial():
    world, case = seeded()
    line = case.line("line-physio-visits")

    assert line.plan_paid == Money.from_dollars("1440.00")
    assert line.patient_responsibility == Money.from_dollars("720.00")
    assert line.is_denied is True
    assert line.is_partial_denial is True


def test_the_old_definition_would_have_hidden_it_completely():
    """Stated as the arithmetic it actually was, so the regression is visible rather
    than described. Under 'the plan paid nothing', this line is a paid line."""
    _, case = seeded()
    line = case.line("line-physio-visits")

    paid_nothing = line.plan_paid.cents == 0
    assert paid_nothing is False
    assert line.is_denied != paid_nothing


def test_it_reaches_the_case_file_as_a_denial_a_person_can_be_told_about():
    """Not merely true of the line object. The triage classified it from CARC 96,
    filed it as a denial, and it is one of the four the household actually has."""
    _, case = seeded()
    denial = case.denials["den-96"]

    assert denial.line_id == "line-physio-visits"
    assert denial.matched_code == "96"
    assert denial.denial_class is DenialClass.COVERAGE
    assert "den-96" in case.denials


def test_and_an_ordinary_copay_on_a_fully_paid_line_is_not_dragged_in_with_it():
    """The mirror failure, which is what makes the first one hard. CARC 1, 2 and 3
    are deductible, coinsurance and copay; they sit on ordinary paid lines. A rule
    reading 'has an adjustment code' as 'denied' would raise three false alarms on
    this file alone."""
    _, case = seeded()
    quiet = case.line("line-physio-eval")

    assert quiet.carc == ("3",)
    assert quiet.patient_responsibility.cents > 0
    assert quiet.adjustment_codes == ()
    assert quiet.is_denied is False
