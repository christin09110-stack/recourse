"""One hospital episode and some outpatient care, as claim lines.

Adaeze's gallbladder came out at St. Brendan's in March; three claims followed —
the hospital, the anaesthetist, the home nursing afterwards. Marcus's back was seen
at Northgate and then in physiotherapy. Most of it was paid, which is what a real
episode looks like: about 19% of in-network claims are denied, and a seeded world
where everything is refused would teach a viewer the wrong shape.

Three of these lines are here to be *ignored*: they carry CARC 1, 2 and 3 —
deductible, coinsurance and copay — which appear on ordinary fully-paid lines. A
triage reading "has an adjustment code" as "denied" would raise three false alarms
on this file alone, so the noise is in the seed and the triage is seen stepping over it.

Patient responsibility is **derived**, never typed: allowed less what the plan
paid. An EOB whose columns do not add up is a defect in the demo rather than in the
product, and the surest way not to type one is not to type the fourth column.
"""

from __future__ import annotations

from datetime import date

from recourse.adapters.frozen import DAYS_INTO_FILING_WINDOW, DAYS_SINCE_UNANSWERED_NOTICE, ago
from recourse.adapters.seed_plans import PLAN_ACA, PLAN_ERISA
from recourse.domain.models import Claim, ClaimLine
from recourse.domain.money import Money
from recourse.domain.types import ServiceType

#: (line_id, description, service days ago, billed, allowed, plan paid, carc, rarc)
_LineSpec = tuple[str, str, int, str, str, str, tuple[str, ...], tuple[str, ...]]

#: (claim_id, plan_id, provider, notice days ago, lines)
_CLAIMS: tuple[tuple[str, str, str, int, tuple[_LineSpec, ...]], ...] = (
    ("claim-facility", PLAN_ACA, "St. Brendan's Regional Medical Center", 158, (
        # $500 of deductible left by March, then 20% coinsurance on the rest.
        ("line-facility-ed", "Emergency department visit, level 4",
         173, "2840.00", "1690.00", "1190.00", ("1",), ()),
        ("line-facility-or", "Laparoscopic cholecystectomy — operating room and recovery",
         172, "18400.00", "11250.00", "9000.00", ("2",), ()),
        ("line-facility-room", "Inpatient room and board, semi-private — 2 days",
         171, "4600.00", "3200.00", "2560.00", ("2",), ()),
    )),
    # The clerical one. The anaesthesia claim went out without the rendering
    # provider's identifier, so CARC 16 arrived narrowed by RARC N290 — a form
    # problem, and the only denial in the file the agent can prepare unaided.
    ("claim-anesthesia", PLAN_ACA, "Brendan Anesthesia Associates",
     DAYS_SINCE_UNANSWERED_NOTICE, (
        ("line-anesthesia", "Anaesthesia, upper abdominal laparoscopy — 95 minutes",
         172, "2150.00", "1290.00", "0.00", ("16",), ("N290",)),
    )),
    # The clinical one, and the reason this appeal has been open 150 days: it is
    # waiting on a letter only the surgeon can write.
    ("claim-homehealth", PLAN_ACA, "Silver Creek Home Health", DAYS_INTO_FILING_WINDOW, (
        ("line-homehealth", "Skilled nursing visit, post-operative wound care — 6 visits",
         165, "1470.00", "1050.00", "0.00", ("50",), ()),
    )),
    ("claim-mri", PLAN_ERISA, "Northgate Imaging", 13, (
        ("line-mri", "MRI lumbar spine without contrast",
         29, "3200.00", "1860.00", "0.00", ("197",), ()),
    )),
    # The partial: eight of twelve physiotherapy visits paid, four refused under
    # the plan's annual visit limit. Money moved and a non-cost-share code still
    # refused part of the line, which is exactly the shape that reading denial as
    # payment-of-zero used to hide.
    ("claim-physio", PLAN_ERISA, "Calloway Physical Therapy", 6, (
        ("line-physio-visits", "Physical therapy, therapeutic exercise — 12 visits",
         45, "2880.00", "2160.00", "1440.00", ("96",), ()),
        ("line-physio-eval", "Physical therapy evaluation",
         48, "240.00", "150.00", "120.00", ("3",), ()),
    )),
)


def _line(spec: _LineSpec, claim_id: str, provider: str, service_date: date) -> ClaimLine:
    allowed, paid = Money.from_dollars(spec[4]), Money.from_dollars(spec[5])
    return ClaimLine(
        line_id=spec[0], claim_id=claim_id, description=spec[1],
        service_date=service_date, provider=provider,
        billed=Money.from_dollars(spec[3]), allowed=allowed, plan_paid=paid,
        patient_responsibility=allowed - paid, carc=spec[6], rarc=spec[7],
    )


def claims() -> dict[str, Claim]:
    """Every claim in the episode, keyed by claim id."""
    built: dict[str, Claim] = {}
    for claim_id, plan_id, provider, notice_days, line_specs in _CLAIMS:
        built[claim_id] = Claim(
            claim_id=claim_id, plan_id=plan_id, provider=provider,
            # Post-service throughout: the care happened and then the refusal
            # arrived, which is the case a household actually finds itself in.
            service_type=ServiceType.POST_SERVICE,
            notice_date=ago(notice_days),
            lines=tuple(
                _line(spec, claim_id, provider, ago(spec[2])) for spec in line_specs
            ),
        )
    return built
