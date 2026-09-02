"""The labelled block at the top of an EOB: who, which claim, and — critically — when.

The notice date is the one field here that is not merely convenient. Every statutory
clock in this domain counts from it, so a document whose notice date we could not
read is a document whose deadlines we cannot compute. `EOBHeader.missing` names that
plainly rather than letting a `None` drift downstream into an arithmetic that would
either crash later or, worse, quietly assume today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from recourse.ingest.text import parse_date

#: Label -> field. Insurers do not agree on wording, so each field carries the
#: spellings seen in the wild. Matching is exact against the normalised label, so
#: "Provider NPI:" does not silently become the provider's name.
LABELS: dict[str, str] = {
    "plan name": "plan_name", "plan": "plan_name", "benefit plan": "plan_name",
    "plan/product": "plan_name", "product": "plan_name",
    "member id": "member_id", "member no": "member_id", "member number": "member_id",
    "subscriber id": "member_id", "member/subscriber id": "member_id", "id number": "member_id",
    "claim number": "claim_id", "claim no": "claim_id", "claim id": "claim_id",
    "claim": "claim_id", "claim reference": "claim_id",
    "notice date": "notice_date", "date of notice": "notice_date", "date issued": "notice_date",
    "processed date": "notice_date", "statement date": "notice_date", "date of this notice": "notice_date",
    "provider": "provider", "rendering provider": "provider", "servicing provider": "provider",
    "facility": "provider", "provider name": "provider",
}
_PUNCTUATION = re.compile(r"[^a-z0-9/ ]+")


@dataclass(frozen=True)
class EOBHeader:
    plan_name: str | None = None
    member_id: str | None = None
    claim_id: str | None = None
    notice_date: date | None = None
    provider: str | None = None

    @property
    def missing(self) -> tuple[str, ...]:
        """Which header fields the document did not yield, notice date first."""
        absent = [name for name in ("notice_date", "member_id", "claim_id", "plan_name", "provider")
                  if getattr(self, name) is None]
        return tuple(absent)


def _normalise(label: str) -> str:
    return _PUNCTUATION.sub("", label.strip().lower()).strip()


def parse_header(lines: tuple[str, ...]) -> EOBHeader:
    """Read the labelled fields. First occurrence of each label wins.

    First-wins because the identifying block is at the top and the same words
    recur in the appeal-rights boilerplate underneath ("...the date of this
    notice..."), where they are prose rather than a value.
    """
    found: dict[str, object] = {}
    for line in lines:
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        field = LABELS.get(_normalise(label))
        value = value.strip()
        if field is None or not value or field in found:
            continue
        if field == "notice_date":
            parsed = parse_date(value)
            if parsed is not None:
                found[field] = parsed
        else:
            found[field] = " ".join(value.split())
    return EOBHeader(**found)  # type: ignore[arg-type]
