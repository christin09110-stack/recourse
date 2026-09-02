"""The committed sample EOBs, parsed once.

The PDFs are checked in rather than generated at test time, so the suite exercises
exactly the bytes a reviewer can open. `tests/fixtures/build_samples.py` regenerates
them and needs `reportlab`; nothing here does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from recourse.ingest import ParsedEOB, parse_eob

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def sample_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture(scope="session")
def aca() -> ParsedEOB:
    """A marketplace plan, a hospital episode, six lines, two of them denied."""
    return parse_eob(sample_bytes("sample-aca-eob.pdf"))


@pytest.fixture(scope="session")
def erisa() -> ParsedEOB:
    """An employer group health plan, four lines, one denied for missing auth."""
    return parse_eob(sample_bytes("sample-erisa-eob.pdf"))


@pytest.fixture(scope="session")
def mangled() -> ParsedEOB:
    """The same shape, with two of its four rows damaged beyond full reading."""
    return parse_eob(sample_bytes("sample-mangled-eob.pdf"))


@pytest.fixture(scope="session")
def unrelated() -> ParsedEOB:
    """A page of hospital prose that is not an EOB at all."""
    return parse_eob(sample_bytes("sample-unrelated.pdf"))
