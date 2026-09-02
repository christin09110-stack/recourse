"""Parsing an EOB PDF into claim lines."""

from __future__ import annotations

from datetime import date

import pytest

from recourse.domain.money import Money
from recourse.ingest import ParsedEOB, parse_eob
from recourse.ingest.lines import UNKNOWN_DATE

from .conftest import sample_bytes


def test_aca_sample_parses_to_six_lines(aca: ParsedEOB) -> None:
    assert len(aca.lines) == 6
    assert aca.warnings == ()


def test_erisa_sample_parses_to_four_lines(erisa: ParsedEOB) -> None:
    assert len(erisa.lines) == 4
    assert erisa.warnings == ()


def test_aca_denials_carry_carc_16_and_carc_50(aca: ParsedEOB) -> None:
    assert [line.carc for line in aca.denied] == [("16",), ("50",)]
    assert [line.rarc for line in aca.denied] == [("N290",), ("N130",)]


def test_erisa_denial_carries_carc_197(erisa: ParsedEOB) -> None:
    (denied,) = erisa.denied
    assert denied.carc == ("197",)
    assert denied.description.startswith("73721")


def test_amounts_are_exact_cents_not_floats(aca: ParsedEOB) -> None:
    first, mri = aca.lines[0], aca.lines[5]
    assert first.billed == Money(cents=248000)  # "2,480.00", not 2480.0
    assert first.allowed == Money(cents=161200)
    assert first.plan_paid == Money(cents=128960)
    assert first.patient_responsibility == Money(cents=32240)
    assert mri.patient_responsibility == Money(cents=315000)


def test_header_fields_are_recovered(aca: ParsedEOB, erisa: ParsedEOB) -> None:
    assert aca.plan_name == "Meridian Silver 3000 HMO (Marketplace)"
    assert aca.member_id == "MHA-4477201983"
    assert aca.claim_id == "2026-CLM-8841203"
    assert aca.notice_date == date(2026, 3, 4)
    assert aca.provider == "Fairhaven Regional Medical Center"
    assert erisa.claim_id == "ERG-2026-0044119"
    assert erisa.notice_date == date(2026, 4, 12)
    assert erisa.header.missing == ()


def test_lines_inherit_the_claim_and_provider(erisa: ParsedEOB) -> None:
    assert {ln.claim_id for ln in erisa.lines} == {"ERG-2026-0044119"}
    assert {ln.provider for ln in erisa.lines} == {"Kestrel Orthopaedic Associates"}


@pytest.mark.parametrize("name", ["sample-aca-eob.pdf", "sample-erisa-eob.pdf"])
def test_parsing_is_deterministic(name: str) -> None:
    assert parse_eob(sample_bytes(name)) == parse_eob(sample_bytes(name))


def test_no_recognisable_row_is_ever_dropped(mangled: ParsedEOB) -> None:
    """Four rows in the table, four lines out — two of them only partly read."""
    assert len(mangled.lines) == 4
    assert len(mangled.flagged) == 2
    assert "2 of 4 service lines could not be fully read" in mangled.warnings


def test_a_damaged_denied_row_still_surfaces_its_carc(mangled: ParsedEOB) -> None:
    """The whole point: the row we could not read is the denial we must not lose."""
    damaged = mangled.flagged
    assert [line.carc for line in damaged] == [("16",), ("50",)]
    assert damaged[0].service_date == date(2026, 6, 1)      # recovered
    assert damaged[1].service_date == UNKNOWN_DATE          # admitted, not guessed
    assert damaged[0].billed == Money.zero()                # never a partial guess
    assert damaged[1].patient_responsibility == Money(cents=194000)


def test_unrelated_text_invents_no_lines(unrelated: ParsedEOB) -> None:
    assert unrelated.lines == ()
    assert unrelated.notice_date is None
    assert "this may not be an EOB" in " ".join(unrelated.warnings)


@pytest.mark.parametrize("payload", [
    b"", b"not a pdf at all", b"%PDF-1.4\n%%EOF\n",
    sample_bytes("sample-aca-eob.pdf")[:900],
    sample_bytes("sample-aca-eob.pdf").replace(b"/Type /Page", b"/Type /Pgxx"),
])
def test_a_broken_file_signals_rather_than_raises(payload: bytes) -> None:
    parsed = parse_eob(payload)
    assert parsed.warnings, "a file we could not read must say so"
    assert parsed.needs_review
    assert all(line.needs_review for line in parsed.lines)
