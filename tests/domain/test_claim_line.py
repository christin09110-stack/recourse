"""What counts as a denial.

The parser must not drop a line, and this must not drop one by arithmetic.
"""

from __future__ import annotations

from datetime import date

from recourse.domain.models import ClaimLine
from recourse.domain.money import Money


def _line(*, carc=(), plan_paid="0.00", owed="100.00") -> ClaimLine:
    return ClaimLine(
        line_id="l", claim_id="c", description="Service", service_date=date(2026, 6, 1),
        provider="A Provider", billed=Money.from_dollars("500.00"),
        allowed=Money.from_dollars("400.00"), plan_paid=Money.from_dollars(plan_paid),
        patient_responsibility=Money.from_dollars(owed), carc=carc,
    )


def test_a_fully_denied_line_is_denied():
    assert _line(carc=("50",)).is_denied is True


def test_a_line_with_no_codes_is_not_denied():
    assert _line(carc=(), plan_paid="400.00", owed="0.00").is_denied is False


def test_an_ordinary_paid_line_carrying_only_cost_share_codes_is_not_denied():
    """Deductible, coinsurance and copay appear on almost every paid line. Treating
    them as denials would bury the real ones in noise."""
    assert _line(carc=("1", "2", "3"), plan_paid="320.00", owed="80.00").is_denied is False


def test_a_partial_denial_is_a_denial():
    """The plan paid the visit and refused part of it. Just as appealable, and the
    old rule - denial means the plan paid nothing - hid every one of them."""
    line = _line(carc=("2", "97"), plan_paid="300.00", owed="100.00")
    assert line.is_denied is True
    assert line.is_partial_denial is True
    assert line.adjustment_codes == ("97",)


def test_a_fully_denied_line_is_not_a_partial_denial():
    assert _line(carc=("50",)).is_partial_denial is False


def test_cost_share_codes_are_stripped_from_the_adjustment_codes():
    assert _line(carc=("1", "197")).adjustment_codes == ("197",)
