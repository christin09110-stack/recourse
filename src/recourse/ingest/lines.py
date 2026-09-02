"""The service table: one `ClaimLine` per row, whatever state the row is in.

**The rule this module exists to enforce.** A row we recognise as a service row but
cannot fully read is returned with `needs_review=True` and whatever we did recover.
It is never dropped, and it never raises.

That is not defensive habit, it is the product's whole premise. Fewer than 1% of
denied claims are ever appealed, and the reason is that nobody notices them. A
parser that quietly discarded a row it found confusing would be manufacturing
exactly the silence we are here to break — and it would do it invisibly, on the one
line most likely to be malformed, which is disproportionately the *denied* line,
because denied lines carry extra reason-code text that pushes the layout around.
Zero amounts plus a flag plus the raw text is honest. A missing row is not.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from recourse.domain.models import ClaimLine
from recourse.domain.money import Money
from recourse.ingest.text import LEADING_DATE_RE, money_tokens, parse_date

_HEADER_WORDS = ("billed", "allowed")
_END_OF_TABLE = re.compile(r"^\s*(totals?|grand total|claim total)\b", re.IGNORECASE)
_RULE_LINE = re.compile(r"^[\s\-=_.]*$")
_CARC = re.compile(r"^\d{1,3}$")
_RARC = re.compile(r"^[A-Z]{1,3}\d{1,3}$")
#: An unknown service date. Deliberately absurd rather than plausible: a flagged
#: line must not carry a date anyone could mistake for one we actually read.
UNKNOWN_DATE = date.min


def candidate_rows(lines: tuple[str, ...]) -> tuple[str, ...]:
    """The lines that are service rows, by the strictest test the document supports.

    Inside a recognised table (a heading naming BILLED and ALLOWED, down to the
    totals) anything date-led or money-heavy is a row, so damaged ones still count.
    With no heading to bound it we demand a leading date *and* four amounts, because
    outside a table the alternative is inventing claim lines out of prose.
    """
    heading = next((i for i, ln in enumerate(lines)
                    if all(word in ln.lower() for word in _HEADER_WORDS)), None)
    if heading is None:
        return tuple(ln for ln in lines
                     if LEADING_DATE_RE.match(ln) and len(money_tokens(ln)) >= 4)
    rows = []
    for line in lines[heading + 1:]:
        if _END_OF_TABLE.match(line):
            break
        if _RULE_LINE.match(line):
            continue
        if LEADING_DATE_RE.match(line) or len(money_tokens(line)) >= 3:
            rows.append(line)
    return tuple(rows)


def _codes(tail: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    carc, rarc = [], []
    for token in re.split(r"[^A-Za-z0-9]+", tail.strip()):
        if _CARC.match(token):
            carc.append(token)
        elif _RARC.match(token.upper()):
            rarc.append(token.upper())
    return tuple(carc), tuple(rarc)


def parse_row(raw: str, line_id: str, claim_id: str) -> ClaimLine:
    """One row. Complete where it can be, flagged where it cannot, always returned."""
    amounts = money_tokens(raw)
    leading = LEADING_DATE_RE.match(raw)
    service_date = parse_date(leading.group(1)) if leading else None
    complete = service_date is not None and len(amounts) >= 4
    # Four amounts or none. A row missing one column would have the rest shifted
    # into the wrong fields, and a wrong figure quoted back at an insurer is worse
    # than an admitted blank - the flag already tells a person to look.
    figures = [a for a, _, _ in amounts[-4:]] if len(amounts) >= 4 else [Money.zero()] * 4
    tail = raw[amounts[-1][2]:] if amounts else raw.rsplit(None, 1)[-1] if raw.split() else ""
    body = raw[leading.end():amounts[-4][1]] if complete else raw
    carc, rarc = _codes(tail)
    return ClaimLine(
        line_id=line_id, claim_id=claim_id, description=" ".join(body.split()),
        service_date=service_date or UNKNOWN_DATE, provider="",
        billed=figures[0], allowed=figures[1], plan_paid=figures[2],
        patient_responsibility=figures[3], carc=carc, rarc=rarc, needs_review=not complete,
    )


def parse_lines(lines: tuple[str, ...], claim_id: str, provider: str = "") -> tuple[ClaimLine, ...]:
    """Every recognised service row, in document order, none of them omitted."""
    rows = candidate_rows(lines)
    parsed = [parse_row(raw, f"{claim_id}-L{number:02d}", claim_id)
              for number, raw in enumerate(rows, start=1)]
    return tuple(replace(line, provider=provider) if provider else line for line in parsed)
