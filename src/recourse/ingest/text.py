"""PDF bytes to text lines, and text tokens to the scalars an EOB carries.

Nothing here decides anything. It reads, and it reports what it could not read,
because every layer above this one is built on the promise that an unreadable thing
is announced rather than skipped.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO

from recourse.domain.money import Money

#: Comma-grouped form first: `\d{1,3}(?:,\d{3})+` would otherwise never match
#: "1,612.00" once the plain alternative had consumed "612.00".
MONEY_RE = re.compile(r"-?\$?\d{1,3}(?:,\d{3})+\.\d{2}|-?\$?\d+\.\d{2}")
LEADING_DATE_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})")
ANY_DATE_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|[A-Z][a-z]{2,8}\.? \d{1,2},? \d{4}",
)
_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y")


def read_text(pdf_bytes: bytes) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Every line of every page, and a warning for every page that would not read.

    A page that raises is reported and skipped rather than aborting the document.
    An EOB whose second page is damaged still carries denials on its first, and
    those denials are the reason this software exists — losing them because of a
    font table we could not decode would be the worst possible trade.
    """
    warnings: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        pages = list(reader.pages)
    except Exception as exc:  # noqa: BLE001 - any pypdf failure is a read failure
        return (), (f"the file could not be opened as a PDF: {type(exc).__name__}: {exc}",)

    lines: list[str] = []
    for number, page in enumerate(pages, start=1):
        try:
            extracted = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"page {number} of {len(pages)} could not be read: {exc}")
            continue
        if not extracted.strip():
            warnings.append(f"page {number} of {len(pages)} held no extractable text")
        lines.extend(extracted.splitlines())
    if not pages:
        warnings.append("the PDF held no pages")
    return tuple(lines), tuple(warnings)


def money_tokens(text: str) -> tuple[tuple[Money, int, int], ...]:
    """Every dollar amount in `text`, with the span it occupied."""
    found = []
    for match in MONEY_RE.finditer(text):
        amount = parse_money(match.group())
        if amount is not None:
            found.append((amount, match.start(), match.end()))
    return tuple(found)


def parse_money(token: str) -> Money | None:
    """`"$1,612.00"` -> 161200 cents. Cents, never a float: see `domain/money.py`."""
    cleaned = token.strip().replace("$", "").replace(",", "").replace(" ", "")
    if not cleaned:
        return None
    try:
        return Money.from_dollars(cleaned)
    except Exception:  # noqa: BLE001 - a malformed amount is data, not a crash
        return None


def parse_date(token: str) -> date | None:
    """The first date in `token`, in any of the forms an EOB is printed in."""
    match = ANY_DATE_RE.search(token)
    if match is None:
        return None
    candidate = match.group().replace(".", "")
    for fmt in _FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None
