"""The classification table, and the line it draws.

The test that matters most is `test_the_line_the_product_turns_on`: CARC 50 is the
clinician's to argue and CARC 16 is a form problem. Everything the agent is allowed
to do alone hangs off that distinction being a lookup rather than a judgement.
"""

from __future__ import annotations

import pytest

from recourse.domain.codes import SEVERITY, classify
from recourse.domain.types import DenialClass

# The nine verified against the X12 list on 2 September 2026.
VERIFIED = [
    ("11", DenialClass.CLERICAL),
    ("16", DenialClass.CLERICAL),
    ("18", DenialClass.CLERICAL),
    ("27", DenialClass.ELIGIBILITY),
    ("29", DenialClass.TIMELINESS),
    ("50", DenialClass.CLINICAL),
    ("96", DenialClass.COVERAGE),
    ("197", DenialClass.AUTHORIZATION),
    ("252", DenialClass.CLERICAL),
]


@pytest.mark.parametrize(("code", "expected"), VERIFIED)
def test_verified_codes_classify_as_documented(code: str, expected: DenialClass) -> None:
    result = classify((code,))
    assert result.denial_class is expected
    assert result.matched is not None
    assert result.matched.code == code


def test_the_line_the_product_turns_on() -> None:
    """CARC 50 is the doctor's argument; CARC 16 is paperwork. Nothing blurs this."""
    assert classify(("50",)).denial_class is DenialClass.CLINICAL
    assert classify(("16",)).denial_class is DenialClass.CLERICAL


def test_unknown_code_is_unassessable_and_says_so() -> None:
    result = classify(("99999",))
    assert result.denial_class is DenialClass.UNASSESSABLE
    assert not result.is_assessable
    assert result.unknown_codes == ("99999",)
    assert "99999" in result.reason
    assert result.matched is None


def test_no_codes_at_all_is_unassessable() -> None:
    """36% of denials list no reason. Silence is escalated, never resolved."""
    result = classify((), ())
    assert result.denial_class is DenialClass.UNASSESSABLE
    assert "no adjustment reason code" in result.reason


def test_an_unknown_code_beside_a_known_one_still_fails_closed() -> None:
    """The code we could not read might be the clinical half of the denial."""
    assert classify(("16", "99999")).denial_class is DenialClass.UNASSESSABLE


def test_several_codes_resolve_by_documented_precedence() -> None:
    """Most serious wins, in the order SEVERITY documents."""
    assert classify(("16", "50")).denial_class is DenialClass.CLINICAL
    assert classify(("197", "16")).denial_class is DenialClass.AUTHORIZATION
    assert classify(("29", "96", "16")).denial_class is DenialClass.TIMELINESS
    assert classify(("96", "27")).denial_class is DenialClass.COVERAGE
    # The matched row is the one that won, not merely the first read.
    assert classify(("16", "50")).matched is not None
    assert classify(("16", "50")).matched.code == "50"


def test_severity_covers_every_denial_class_exactly_once() -> None:
    assert set(SEVERITY) == set(DenialClass)
    assert len(SEVERITY) == len(DenialClass)
