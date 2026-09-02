"""The nouns.

Deliberately dumb: these hold facts and answer questions about themselves. Nothing
here computes a deadline or decides what a denial means — that lives in `clocks.py`
and `codes.py`, as pure functions, so that no object flowing through the agent can
quietly disagree with the arithmetic.

This module is the *record* — what the insurer said and what the file holds. What we
intend to do about it (assertions, appeals, clocks, escalations) lives in `appeal.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from recourse.domain.money import Money
from recourse.domain.types import DenialClass, PlanType, ServiceType


@dataclass(frozen=True)
class Plan:
    plan_id: str
    name: str
    plan_type: PlanType
    member_id: str
    #: ERISA plans may require one or two mandatory internal appeals before a civil
    #: action (29 CFR 2560.503-1 (c)(2)). ACA marketplace plans are always one.
    internal_levels: int = 1
    #: Non-grandfathered plans carry the ACA external review right; grandfathered
    #: ERISA plans do not, and their next step after exhaustion is a civil action.
    grandfathered: bool = False
    appeals_address: str = ""


@dataclass(frozen=True)
class Document:
    """Something in the case file that an assertion may cite."""

    document_id: str
    kind: str          # "eob" | "denial_letter" | "authorization" | "clinical_note" | ...
    title: str
    received_on: date
    #: Extracted text, where there is any. Absent for a scan nobody has read.
    text: str = ""


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
    def is_denied(self) -> bool:
        return bool(self.carc) and self.plan_paid.cents == 0


@dataclass(frozen=True)
class Claim:
    claim_id: str
    plan_id: str
    provider: str
    service_type: ServiceType
    #: The date on the notice, which is what every clock counts from.
    notice_date: date
    lines: tuple[ClaimLine, ...] = ()

    @property
    def denied_lines(self) -> tuple[ClaimLine, ...]:
        return tuple(line for line in self.lines if line.is_denied)

    @property
    def denied_total(self) -> Money:
        total = Money.zero()
        for line in self.denied_lines:
            total = total + line.patient_responsibility
        return total


@dataclass(frozen=True)
class Denial:
    """One denied line, once it has been classified."""

    denial_id: str
    claim_id: str
    line_id: str
    denial_class: DenialClass
    #: The code row the classification came from, so the console can show its source.
    matched_code: str
    reason_text: str
