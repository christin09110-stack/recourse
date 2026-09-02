"""Reading text out of a PDF, and scalars out of text."""

from __future__ import annotations

from datetime import date

import pytest

from recourse.domain.money import Money
from recourse.ingest.text import money_tokens, parse_date, parse_money, read_text


@pytest.mark.parametrize(("token", "cents"), [
    ("$1,612.00", 161200), ("1289.60", 128960), ("0.00", 0),
    ("-322.40", -32240), ("$3,150.00", 315000), ("7,108.00", 710800),
])
def test_amounts_parse_to_exact_cents(token: str, cents: int) -> None:
    assert parse_money(token) == Money(cents=cents)


def test_a_malformed_amount_is_none_rather_than_an_exception() -> None:
    assert parse_money("###.##") is None
    assert parse_money("") is None
    assert money_tokens("06/01/2026 J1885 Ketorolac ###.## ?") == ()


def test_money_is_found_with_and_without_thousands_separators() -> None:
    found = [amount for amount, _, _ in money_tokens("2,480.00 1,612.00 1289.60 322.40")]
    assert found == [Money(cents=248000), Money(cents=161200),
                     Money(cents=128960), Money(cents=32240)]


@pytest.mark.parametrize(("token", "expected"), [
    ("03/04/2026", date(2026, 3, 4)), ("2026-03-04", date(2026, 3, 4)),
    ("March 4, 2026", date(2026, 3, 4)), ("Notice Date: 3/4/26", date(2026, 3, 4)),
])
def test_dates_parse_in_the_forms_an_eob_is_printed_in(token: str, expected: date) -> None:
    assert parse_date(token) == expected


def test_an_unreadable_page_is_reported_and_the_rest_survive(monkeypatch: pytest.MonkeyPatch) -> None:
    """One bad page must not cost us the denials printed on the good one."""

    class Boom:
        def extract_text(self) -> str:
            raise RuntimeError("bad font table")

    class Fine:
        def extract_text(self) -> str:
            return "02/14/2026 80053 Panel 186.00 0.00 0.00 186.00 16"

    class Reader:
        def __init__(self, _stream: object) -> None:
            self.pages = [Boom(), Fine()]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", Reader)
    lines, warnings = read_text(b"%PDF-1.4")
    assert lines == ("02/14/2026 80053 Panel 186.00 0.00 0.00 186.00 16",)
    assert warnings == ("page 1 of 2 could not be read: bad font table",)
