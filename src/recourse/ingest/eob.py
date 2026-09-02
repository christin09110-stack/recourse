"""Parse an uploaded Explanation of Benefits into claim lines.

`parse_eob` is total: it returns a `ParsedEOB` for every input, including bytes that
are not a PDF at all. Nothing it can be handed makes it raise, because the caller is
an agent loop processing a person's mail, and an exception there is a denial that
never gets triaged.

What it will not do is invent. A file it could not read comes back with no lines and
a warning saying so; a row it could not read comes back flagged. The two failures
are reported differently on purpose — one means "look at this document", the other
means "look at this line" — and neither is ever silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from recourse.domain.models import ClaimLine
from recourse.ingest.header import EOBHeader, parse_header
from recourse.ingest.lines import parse_lines
from recourse.ingest.text import read_text


@dataclass(frozen=True)
class ParsedEOB:
    """What one uploaded EOB yielded, and everything it did not."""

    lines: tuple[ClaimLine, ...] = ()
    plan_name: str | None = None
    member_id: str | None = None
    claim_id: str | None = None
    #: The date every statutory clock counts from. `None` means we could not read it,
    #: which downstream must treat as "cannot compute deadlines", never as today.
    notice_date: date | None = None
    provider: str | None = None
    #: Document-level problems in plain English, for a person to read.
    warnings: tuple[str, ...] = ()

    @property
    def flagged(self) -> tuple[ClaimLine, ...]:
        """The lines a person has to look at before this EOB can be trusted."""
        return tuple(line for line in self.lines if line.needs_review)

    @property
    def denied(self) -> tuple[ClaimLine, ...]:
        return tuple(line for line in self.lines if line.is_denied)

    @property
    def needs_review(self) -> bool:
        """True if anything at all about this document is unresolved."""
        return bool(self.warnings) or bool(self.flagged) or self.notice_date is None

    @property
    def header(self) -> EOBHeader:
        return EOBHeader(self.plan_name, self.member_id, self.claim_id,
                         self.notice_date, self.provider)


def parse_eob(pdf_bytes: bytes, *, fallback_claim_id: str = "unknown-claim") -> ParsedEOB:
    """Read an EOB PDF. Never raises; never drops a recognised service row.

    `fallback_claim_id` is only used to build line ids when the document does not
    name its own claim number — the lines still have to be addressable, because a
    claim number we could not read is precisely the case where someone needs to open
    the document and check.
    """
    lines, warnings = read_text(pdf_bytes)
    if not lines:
        return ParsedEOB(warnings=warnings or ("no text could be extracted from the file",))

    header = parse_header(lines)
    claim_id = header.claim_id or fallback_claim_id
    claim_lines = parse_lines(lines, claim_id, header.provider or "")

    notes = list(warnings)
    if not claim_lines:
        notes.append("no service lines were recognised: this may not be an EOB")
    if header.notice_date is None:
        notes.append("no notice date was found, so no appeal deadline can be computed")
    flagged = sum(1 for line in claim_lines if line.needs_review)
    if flagged:
        notes.append(f"{flagged} of {len(claim_lines)} service lines could not be fully read")

    return ParsedEOB(
        lines=claim_lines, plan_name=header.plan_name, member_id=header.member_id,
        claim_id=header.claim_id, notice_date=header.notice_date,
        provider=header.provider, warnings=tuple(notes),
    )
