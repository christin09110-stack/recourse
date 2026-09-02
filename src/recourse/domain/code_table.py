"""The X12 code table, as data.

Kept apart from `codes.py` so the classification rules and the rows they read are
separately reviewable — and so a row added by someone reading the X12 lists never
requires touching the logic that decides what a row means.

Every row carries the URL it was read from. A figure in an appeal letter with no
provenance is a figure the person sending it cannot defend, so provenance is a field
rather than a comment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from recourse.domain.types import DenialClass

#: `domain/` and `rulebook/` are siblings under `src/recourse/`.
DATA_PATH = Path(__file__).resolve().parent.parent / "rulebook" / "data" / "codes.json"


@dataclass(frozen=True)
class CodeRow:
    """One published code, and what kind of refusal it signals."""

    code: str
    system: str            # "CARC" or "RARC"
    text: str              # the X12 wording, verbatim
    denial_class: DenialClass
    citation: str
    #: True where the code names no particular problem — CARC 16 covers every
    #: submission error there is. A generic row is the only kind a RARC may narrow.
    generic: bool = False

    @property
    def label(self) -> str:
        return f"{self.system} {self.code}"


def normalise(code: str) -> str:
    """Codes arrive off a PDF with stray spacing and case. `n30` is `N30`."""
    return code.strip().upper()


@lru_cache(maxsize=1)
def code_table() -> dict[tuple[str, str], CodeRow]:
    """Every row, keyed by (system, code). Read once; the file never changes at run time."""
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    table: dict[tuple[str, str], CodeRow] = {}
    for entry in raw["codes"]:
        row = CodeRow(
            code=normalise(entry["code"]),
            system=normalise(entry["system"]),
            text=entry["text"],
            denial_class=DenialClass(entry["denial_class"]),
            citation=entry["citation"],
            generic=bool(entry.get("generic", False)),
        )
        table[(row.system, row.code)] = row
    return table


def lookup(system: str, code: str) -> CodeRow | None:
    return code_table().get((normalise(system), normalise(code)))


def split_known(system: str, codes: tuple[str, ...]) -> tuple[list[CodeRow], tuple[str, ...]]:
    """Recognised rows, and the codes that matched nothing.

    The unrecognised half is returned rather than dropped: a code this build has not
    heard of is the fact the caller most needs.
    """
    known: list[CodeRow] = []
    unknown: list[str] = []
    for code in codes:
        row = lookup(system, code)
        if row is None:
            unknown.append(normalise(code))
        else:
            known.append(row)
    return known, tuple(unknown)
