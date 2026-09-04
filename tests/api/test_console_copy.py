"""The console's own copy, checked against the rulebook it describes.

The Autonomy screen carries the statute behind each non-negotiable rule as console
copy, because the API sends only the rule names. That copy can therefore drift from
the data without anything failing — and it had. It cited 29 CFR 2560.503-1(h)(2)(i)
for the 180-day appeal window, which is the subsection giving *60* days to non-health
plans; the 180 days is (h)(3)(i).

That is precisely the confusion the whole design is built to avoid, printed on the
screen that advertises the rule, under a heading about never letting a deadline pass.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ROOT / "frontend" / "src" / "views.jsx"
DATA = ROOT / "src" / "recourse" / "rulebook" / "data"

#: (subsection, the number of days it actually grants)
SUBSECTIONS = {"(h)(3)(i)": "180", "(h)(2)(i)": "60"}


def _statutes() -> list[str]:
    if not VIEWS.exists():  # pragma: no cover - the console is optional at test time
        pytest.skip("no console checked out")
    return re.findall(r"statute:\s*'([^']*)'", VIEWS.read_text())


def test_no_statute_line_pairs_a_subsection_with_the_wrong_number_of_days():
    wrong = []
    for line in _statutes():
        for subsection, correct in SUBSECTIONS.items():
            if subsection not in line:
                continue
            said = re.search(r"\b(\d+)\s+days", line)
            if said and said.group(1) != correct:
                wrong.append(f"{line!r} says {said.group(1)} days; {subsection} gives {correct}")
    assert not wrong, wrong


def test_the_rulebook_and_the_console_agree_on_which_subsection_grants_180_days():
    """The data is the authority. If it moves, this fails rather than the screen
    quietly telling somebody they have four months they do not have."""
    erisa = json.loads((DATA / "erisa-group-health.json").read_text())
    note = erisa["time_to_appeal"].get("note", "")
    assert "(h)(3)(i)" in note
    assert any("(h)(3)(i)" in line for line in _statutes()), (
        "the console cites no subsection that matches the rulebook's 180-day figure"
    )
