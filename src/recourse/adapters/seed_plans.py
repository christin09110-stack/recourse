"""The household's two plans, and the paperwork it already holds.

One family, two policies, because that is the ordinary case and because it is the
only way to show the two clock regimes side by side: Adaeze is self-employed and
buys on the marketplace, Marcus is covered through his employer under a plan
governed by ERISA. The ERISA plan requires **two** mandatory internal appeals
(29 CFR 2560.503-1(c)(2)), so a denial there has one more door to go through than
the same denial on the marketplace plan — and `internal_levels` here has to agree
with the rulebook file, or the clocks split a 60-day answer that the plan never
divides. The adapter tests check that agreement rather than trusting it.

**The case file deliberately holds no `clinical_note`.** `evidence.gaps` searches
the whole file by document kind, so a letter of medical necessity filed for any
reason at all would close the gap on the CARC 50 denial and quietly turn the one
denial Recourse is supposed to hand back into one it thinks it can draft. The
absence is the demo, and it is fragile: adding a clinical note here breaks it.
"""

from __future__ import annotations

from recourse.adapters.frozen import ago
from recourse.domain.models import Document, Plan
from recourse.domain.types import PlanType

PLAN_ACA = "plan-aca"
PLAN_ERISA = "plan-erisa"


def plans() -> dict[str, Plan]:
    """Adaeze's marketplace plan and Marcus's employer plan."""
    return {
        PLAN_ACA: Plan(
            plan_id=PLAN_ACA,
            name="Harbor Blue Silver Plus",
            plan_type=PlanType.ACA_MARKETPLACE,
            member_id="HB-4417-8820",
            internal_levels=1,
            grandfathered=False,
            appeals_address="Harbor Blue Appeals Unit, PO Box 4412, Trenton NJ 08650",
        ),
        PLAN_ERISA: Plan(
            plan_id=PLAN_ERISA,
            name="Meridian Health PPO — Calloway Foods Group Plan",
            plan_type=PlanType.ERISA_GROUP_HEALTH,
            member_id="MER-90233-01",
            # Two mandatory levels, and non-grandfathered, so external review still
            # follows exhaustion rather than a civil action under 502(a).
            internal_levels=2,
            grandfathered=False,
            appeals_address="Meridian Health Appeals, 900 Kestrel Way, Columbus OH 43215",
        ),
    }


#: (document_id, kind, title, days before the frozen today it arrived)
_DOCS: tuple[tuple[str, str, str, int], ...] = (
    ("doc-eob-facility", "eob", "EOB — St. Brendan's Regional Medical Center", 154),
    ("doc-eob-anesthesia", "eob", "EOB — Brendan Anesthesia Associates", 75),
    ("doc-eob-homehealth", "eob", "EOB — Silver Creek Home Health", 146),
    ("doc-eob-mri", "eob", "EOB — Northgate Imaging", 9),
    ("doc-eob-physio", "eob", "EOB — Calloway Physical Therapy", 2),
    ("doc-denial-homehealth", "denial_letter",
     "Harbor Blue adverse benefit determination — skilled nursing visits", 146),
    # The one that lands on camera. Meridian approved the lumbar MRI five weeks
    # before it was performed and then denied the claim for absent authorisation:
    # the approval was in this household's file the whole time, and nobody had
    # attached it to the claim.
    ("doc-auth-mri", "authorization",
     "Meridian Health prior authorisation approval — MRI lumbar spine, ref PA-4471903", 40),
)


def documents() -> dict[str, Document]:
    """Everything already in the file. No clinical note: see the module docstring."""
    return {
        doc_id: Document(
            document_id=doc_id, kind=kind, title=title, received_on=ago(days_ago),
        )
        for doc_id, kind, title, days_ago in _DOCS
    }
