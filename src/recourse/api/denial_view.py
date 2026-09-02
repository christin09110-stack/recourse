"""One denial, as the console shows it: its class, its source and its gaps.

Nothing here decides anything. The class comes from `codes.classify` and the gaps
from `evidence`, so a screen cannot show a denial as clerical while the engine
treats it as clinical — and `can_prepare_alone` is the engine's own answer, not a
rule about gaps re-derived in a view. A clinical denial with every document in the
file is still not preparable alone: the gap there is authorship, and a view that
worked it out from the gap list would quietly hand back the one denial this product
exists to hand over.
"""

from __future__ import annotations

from typing import Any

from recourse.api.serialise import line_view
from recourse.domain import evidence
from recourse.domain.case import CaseFile
from recourse.domain.codes import classify
from recourse.domain.models import Denial


def denial_view(case: CaseFile, denial: Denial) -> dict[str, Any]:
    """One denial, its class, the row that produced it and what the file lacks."""
    line = case.line(denial.line_id)
    found = classify(line.carc, line.rarc) if line else None
    gaps = evidence.gaps(case, denial.denial_class)
    return {
        "denial_id": denial.denial_id,
        "claim_id": denial.claim_id,
        "line_id": denial.line_id,
        "denial_class": denial.denial_class.value,
        "matched_code": denial.matched_code,
        "reason_text": denial.reason_text,
        "citation": found.matched.citation if found and found.matched else "",
        "narrowed_by": found.detail.label if found and found.detail else None,
        "unknown_codes": list(found.unknown_codes) if found else [],
        "line": line_view(line) if line else None,
        "requirements": [
            {"kind": r.kind, "why": r.why, "required": r.required}
            for r in evidence.requirements_for(denial.denial_class)
        ],
        "gaps": [{"kind": r.kind, "why": r.why} for r in gaps],
        "can_prepare_alone": evidence.can_prepare_alone(case, denial.denial_class),
    }
