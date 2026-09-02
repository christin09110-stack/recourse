"""The data file itself: every row usable, cited, and reachable.

A wrong code text quoted back at an insurer is worse than a smaller table, so these
guard the shape of the data rather than the logic that reads it.
"""

from __future__ import annotations

import json

from recourse.domain.code_table import DATA_PATH, code_table, lookup, split_known
from recourse.domain.codes import classify


def test_every_row_has_a_citation_and_a_valid_class() -> None:
    from recourse.domain.types import DenialClass

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert len(raw["codes"]) >= 30
    for entry in raw["codes"]:
        assert entry["citation"].strip(), entry["code"]
        assert entry["text"].strip(), entry["code"]
        DenialClass(entry["denial_class"])  # raises on an invented class
        expected = "claim-adjustment" if entry["system"] == "CARC" else "remittance-advice"
        assert expected in entry["citation"], entry["code"]


def test_no_row_is_defined_twice() -> None:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    keys = [(e["system"], e["code"]) for e in raw["codes"]]
    assert len(keys) == len(set(keys))


def test_the_table_ships_both_code_systems() -> None:
    systems = {system for system, _ in code_table()}
    assert systems == {"CARC", "RARC"}
    carc = [c for s, c in code_table() if s == "CARC"]
    assert len(carc) >= 30


def test_every_specific_carc_row_classifies_to_its_own_class() -> None:
    """No row is unreachable or contradicts the class it declares."""
    for (system, code), row in code_table().items():
        if system != "CARC" or row.generic:
            continue  # a generic row's class can be narrowed by a remark code
        assert classify((code,)).denial_class is row.denial_class, code


def test_codes_are_normalised_before_lookup() -> None:
    """Codes come off a PDF with stray spacing and case."""
    assert lookup("carc", " 50 ") is not None
    assert classify((" 50 ",), ("m51",)).denial_class.value == "clinical"


def test_split_known_returns_the_unrecognised_half_rather_than_dropping_it() -> None:
    known, unknown = split_known("CARC", ("16", "99999"))
    assert [row.code for row in known] == ["16"]
    assert unknown == ("99999",)
