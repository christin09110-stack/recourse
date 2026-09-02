"""A remark code narrowing a generic reason code.

CARC 16 says only "something is wrong with the paperwork". The RARCs beside it say
which paperwork, and that is often the difference between a denial the agent can
prepare alone and one that belongs to somebody else.
"""

from __future__ import annotations

from recourse.domain.codes import classify
from recourse.domain.types import DenialClass


def test_a_remark_code_narrows_a_generic_carc() -> None:
    """CARC 16 with a missing/incomplete/invalid RARC stays clerical and gains detail."""
    result = classify(("16",), ("M76",))
    assert result.denial_class is DenialClass.CLERICAL
    assert result.matched is not None and result.matched.code == "16"
    assert result.detail is not None and result.detail.code == "M76"
    assert "M76" in result.reason
    assert "diagnosis" in result.detail.text.lower()


def test_a_remark_code_can_move_a_generic_carc_to_another_class() -> None:
    """N30 says the paperwork problem is eligibility, and that changes the route."""
    result = classify(("16",), ("N30",))
    assert result.denial_class is DenialClass.ELIGIBILITY
    assert result.detail is not None and result.detail.code == "N30"


def test_a_remark_code_does_not_override_a_specific_carc() -> None:
    """CARC 50 already names the problem; a clerical remark cannot demote it."""
    assert classify(("50",), ("M51",)).denial_class is DenialClass.CLINICAL


def test_an_unrecognised_remark_code_is_reported_but_not_fatal() -> None:
    """The CARC is the reason; a remark code only qualifies it."""
    result = classify(("50",), ("ZZ999",))
    assert result.denial_class is DenialClass.CLINICAL
    assert result.unknown_codes == ("ZZ999",)
