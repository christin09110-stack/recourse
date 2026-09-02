"""The case file: everything known about one household's episode.

It sits in its own module because it is the one object that spans both halves of the
domain — the record in `models.py` and the intent in `appeal.py` — and importing it
from either would put a cycle between them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from recourse.domain.appeal import Appeal
from recourse.domain.models import Claim, ClaimLine, Denial, Document, Plan


@dataclass
class CaseFile:
    """Everything known about one household's episode."""

    case_id: str
    plans: dict[str, Plan] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    documents: dict[str, Document] = field(default_factory=dict)
    denials: dict[str, Denial] = field(default_factory=dict)
    appeals: dict[str, Appeal] = field(default_factory=dict)

    def line(self, line_id: str) -> ClaimLine | None:
        for claim in self.claims.values():
            for line in claim.lines:
                if line.line_id == line_id:
                    return line
        return None

    def claim_for_line(self, line_id: str) -> Claim | None:
        for claim in self.claims.values():
            if any(line.line_id == line_id for line in claim.lines):
                return claim
        return None

    def documents_of_kind(self, kind: str) -> tuple[Document, ...]:
        return tuple(d for d in self.documents.values() if d.kind == kind)
