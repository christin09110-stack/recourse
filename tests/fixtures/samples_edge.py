"""The two samples that exist to be difficult.

MANGLED is the important one. Its second row lost its amounts and its third lost
its service date, and both of those rows are denials — which is the realistic case,
because a denied row carries extra reason-code text and is the likeliest to break
the layout. The parser must return four lines for four rows regardless.
"""

from __future__ import annotations

from samples_data import Sample, row  # noqa: TID251 - sibling module, run as a script

MANGLED = Sample(
    filename="sample-mangled-eob.pdf",
    insurer="Meridian Health Alliance",
    header=(("Member ID:", "MHA-4477201983"), ("Claim Number:", "2026-CLM-9910044"), ("Notice Date:", "05/02/2026")),
    rows=(
        row("06/01/2026", "99213", "Office visit, established", ("180.00", "112.00", "89.60", "22.40")),
        row("06/01/2026", "J1885", "Ketorolac injection", ("###.##", "?", "", ""), "16"),
        {"date": "", "proc": "", "desc": "  95810  Sleep study, attended", "billed": "1,940.00",
         "allowed": "0.00", "paid": "0.00", "resp": "1,940.00", "codes": "50"},
        row("06/02/2026", "36415", "Collection of venous blood", ("42.00", "26.00", "20.80", "5.20")),
    ),
    totals=("2,162.00", "138.00", "110.40", "1,967.60"),
    legend=("16  Claim/service lacks information or has submission/billing error(s).",),
)

UNRELATED = Sample(
    filename="sample-unrelated.pdf",
    insurer="Fairhaven Regional Medical Center",
    header=(("Re:", "Parking validation for visitors"),),
    rows=(),
    totals=("", "", "", ""),
    legend=(
        "Visitor parking is validated at the main desk on 03/14/2026 and thereafter.",
        "The daily rate is 12.00 and the weekly maximum is 45.00 for registered families.",
        "Questions about the shuttle timetable should go to the volunteer office.",
    ),
    subtitle="NOTICE TO VISITORS FROM THE FACILITIES OFFICE",
)

ALL: tuple[Sample, ...] = (MANGLED, UNRELATED)
