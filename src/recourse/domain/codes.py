"""What kind of refusal this is, read from the claim's own X12 codes.

This is the lookup the whole product rests on. It draws the line between a denial a
diligent agent can genuinely prepare alone and one that is the treating clinician's
argument and nobody else's — and it draws it from a published code rather than from
an interpretation of the service description.

**Unknown is never a guess.** About 36% of in-network denials are reported with no
reason listed at all (KFF, 2024 marketplace brief). An unrecognised or absent code
returns UNASSESSABLE, which escalates. The honest answer to a reason the insurer
declined to give is to say so.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.code_table import CodeRow, code_table, split_known
from recourse.domain.types import DenialClass

#: Precedence, most serious first, for a line carrying several CARCs. The ordering is
#: *how much human judgement the route needs*, descending — not how much money is at
#: stake — because the only decision this table makes is who handles the denial.
#:
#: UNASSESSABLE leads: a reason we could not read might be anything, clinical
#: included, and drafting against a denial we have only partly read is worse than
#: saying we cannot read it. CLINICAL next: only the treating clinician can argue it.
#: TIMELINESS above the rest because the window may already have shut, the one
#: irreversible outcome here. Then COVERAGE (an argument against plan language),
#: ELIGIBILITY (answerable, but from records held elsewhere), AUTHORIZATION (often
#: resolvable from a letter already in the file) and CLERICAL last — the class the
#: agent can prepare unaided has the weakest claim on a person's attention.
SEVERITY: tuple[DenialClass, ...] = (
    DenialClass.UNASSESSABLE,
    DenialClass.CLINICAL,
    DenialClass.TIMELINESS,
    DenialClass.COVERAGE,
    DenialClass.ELIGIBILITY,
    DenialClass.AUTHORIZATION,
    DenialClass.CLERICAL,
)


@dataclass(frozen=True)
class Classification:
    """A class, and the row that produced it, so the console can show its source."""

    denial_class: DenialClass
    #: The CARC row the class came from. None when nothing was recognised.
    matched: CodeRow | None = None
    #: A RARC that narrowed a generic CARC, where one did.
    detail: CodeRow | None = None
    unknown_codes: tuple[str, ...] = ()
    reason: str = ""

    @property
    def is_assessable(self) -> bool:
        return self.denial_class is not DenialClass.UNASSESSABLE


def _most_serious(rows: list[CodeRow]) -> CodeRow:
    return min(rows, key=lambda row: SEVERITY.index(row.denial_class))


def classify(carc: tuple[str, ...], rarc: tuple[str, ...] = ()) -> Classification:
    """Classify a denied line from its CARCs, narrowed by its RARCs where they help."""
    if not carc:
        return Classification(
            DenialClass.UNASSESSABLE,
            reason="the line carries no adjustment reason code, so there is nothing to read",
        )
    known, unknown = split_known("CARC", carc)
    if unknown:
        # Fail closed even when a sibling code *was* recognised: the code we could not
        # read might be the clinical half of the denial.
        return Classification(
            DenialClass.UNASSESSABLE,
            unknown_codes=unknown,
            reason=f"CARC {', '.join(unknown)} is not in the X12 table this build ships",
        )

    matched = _most_serious(known)
    remarks, stray = split_known("RARC", rarc)
    if matched.generic and remarks:
        # CARC 16 says only "something is wrong with the paperwork". Its remark codes
        # say which paperwork; a missing/incomplete/invalid one leaves it clerical.
        detail = _most_serious(remarks)
        why = f"{matched.label} narrowed by {detail.label}: {detail.text}"
        return Classification(detail.denial_class, matched, detail, stray, why)
    return Classification(
        matched.denial_class, matched, None, stray, f"{matched.label}: {matched.text}",
    )


__all__ = ["SEVERITY", "Classification", "CodeRow", "classify", "code_table"]
