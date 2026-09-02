"""One service on an Explanation of Benefits, and what counts as refused.

The definition of `is_denied` is load-bearing. Reading it as "the plan paid nothing"
hides partial denials - the plan pays the visit and refuses a modifier, or cuts the
units billed - which are every bit as appealable. That is the same failure as
dropping a line in the parser, arrived at by arithmetic instead of by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from recourse.domain.money import Money


#: Deductible, coinsurance and copay. Present on ordinary paid lines, and the
#: reason `is_denied` cannot simply ask whether any code is attached.
_COST_SHARE_CARC = frozenset({"1", "2", "3"})


@dataclass(frozen=True)
class ClaimLine:
    """One service on an Explanation of Benefits."""

    line_id: str
    claim_id: str
    description: str
    service_date: date
    provider: str
    billed: Money
    allowed: Money
    plan_paid: Money
    patient_responsibility: Money
    #: X12 Claim Adjustment Reason Codes, and the Remark Codes that qualify them.
    carc: tuple[str, ...] = ()
    rarc: tuple[str, ...] = ()
    #: Set when the parser could not read the line. Such a line is surfaced for a
    #: human, never dropped: a silently discarded denial is the exact failure this
    #: product exists to prevent.
    needs_review: bool = False

    @property
    def adjustment_codes(self) -> tuple[str, ...]:
        """The CARCs that mean something was refused, not merely cost-shared.

        Codes 1, 2 and 3 are deductible, coinsurance and copay. They appear on
        ordinary fully-paid lines and are not denials of anything.
        """
        return tuple(code for code in self.carc if code not in _COST_SHARE_CARC)

    @property
    def is_denied(self) -> bool:
        """Whether anything on this line was refused.

        Deliberately not "the plan paid nothing". A partial denial - the plan pays
        the visit but refuses a modifier, or cuts the units billed - leaves a
        non-zero `plan_paid` and is every bit as appealable. Reading denial as
        payment-of-zero hid exactly those, which is the same failure as dropping a
        line in the parser, arrived at by arithmetic instead.
        """
        return bool(self.adjustment_codes)

    @property
    def is_partial_denial(self) -> bool:
        """Refused in part: money moved, and a code says some of it was withheld."""
        return self.is_denied and self.plan_paid.cents > 0
