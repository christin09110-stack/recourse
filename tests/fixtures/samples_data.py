"""The literal content of the sample EOBs. Invented insurers, real X12 codes.

Four documents, because the parser has four things to prove: an ACA episode with
two denials, an ERISA episode with one, a table whose rows are damaged (the parser
must still return one line per row, flagged), and a page that is not an EOB at all
(the parser must invent nothing).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    filename: str
    insurer: str
    header: tuple[tuple[str, str], ...]
    rows: tuple[dict[str, str], ...]
    totals: tuple[str, str, str, str]
    legend: tuple[str, ...] = ()
    rights: tuple[str, ...] = ()
    subtitle: str = "EXPLANATION OF BENEFITS  —  THIS IS NOT A BILL"


def row(date: str, proc: str, desc: str, amounts: tuple[str, str, str, str], codes: str = "--") -> dict[str, str]:
    billed, allowed, paid, resp = amounts
    return {"date": date, "proc": proc, "desc": desc, "billed": billed,
            "allowed": allowed, "paid": paid, "resp": resp, "codes": codes}


ACA = Sample(
    filename="sample-aca-eob.pdf",
    insurer="Meridian Health Alliance",
    header=(
        ("Member:", "Dolores A. Whitfield"),
        ("Member ID:", "MHA-4477201983"),
        ("Group:", "Individual Marketplace"),
        ("Plan Name:", "Meridian Silver 3000 HMO (Marketplace)"),
        ("Claim Number:", "2026-CLM-8841203"),
        ("Notice Date:", "03/04/2026"),
        ("Provider:", "Fairhaven Regional Medical Center"),
    ),
    rows=(
        row("02/14/2026", "99285", "Emergency dept visit, level 5", ("2,480.00", "1,612.00", "1,289.60", "322.40")),
        row("02/14/2026", "70450", "CT head/brain w/o contrast", ("940.00", "611.00", "488.80", "122.20")),
        row("02/14/2026", "71046", "Chest X-ray, 2 views", ("310.00", "188.00", "150.40", "37.60")),
        row("02/14/2026", "80053", "Comprehensive metabolic panel", ("186.00", "0.00", "0.00", "186.00"), "16 / N290"),
        row("02/14/2026", "36415", "Collection of venous blood", ("42.00", "26.00", "20.80", "5.20")),
        row("02/15/2026", "70553", "MRI brain w/ and w/o contrast", ("3,150.00", "0.00", "0.00", "3,150.00"), "50 / N130"),
    ),
    totals=("7,108.00", "2,437.00", "1,949.60", "3,823.40"),
    legend=(
        "16  Claim/service lacks information or has submission/billing error(s).",
        "N290  Missing/incomplete/invalid rendering provider primary identifier.",
        "50  These are non-covered services because this is not deemed a medical necessity by the payer.",
        "N130  Consult plan benefit documents/guidelines for information about restrictions for this service.",
    ),
    rights=(
        "If you disagree with this decision you may file an internal appeal within 180 days of the date of this notice.",
        "After a final internal denial you have 4 months to request an external review by an independent reviewer.",
    ),
)

ERISA = Sample(
    filename="sample-erisa-eob.pdf",
    insurer="Cordell Mutual Benefit Administrators",
    header=(
        ("Member:", "Rosalind K. Abara"),
        ("Member ID:", "CMB-2018844-01"),
        ("Plan Name:", "Northgate Industries Group Health Plan"),
        ("Plan Type:", "Employer group health plan (self-funded, ERISA)"),
        ("Claim Number:", "ERG-2026-0044119"),
        ("Notice Date:", "04/12/2026"),
        ("Provider:", "Kestrel Orthopaedic Associates"),
    ),
    rows=(
        row("03/27/2026", "29881", "Knee arthroscopy w/ meniscectomy", ("6,400.00", "3,980.00", "3,184.00", "796.00")),
        row("03/27/2026", "01382", "Anesthesia, knee arthroscopy", ("1,250.00", "742.00", "593.60", "148.40")),
        row("03/27/2026", "73721", "MRI knee w/o contrast", ("1,880.00", "0.00", "0.00", "1,880.00"), "197 / N130"),
        row("04/03/2026", "97110", "Therapeutic exercise, 15 min", ("220.00", "138.00", "110.40", "27.60")),
    ),
    totals=("9,750.00", "4,860.00", "3,888.00", "2,852.00"),
    legend=(
        "197  Precertification/authorization/notification/pre-treatment absent.",
        "N130  Consult plan benefit documents/guidelines for information about restrictions for this service.",
    ),
    rights=(
        "You have 180 days from the date of this notice to file a first-level appeal, and this plan requires two",
        "internal levels before you may bring a civil action under ERISA section 502(a).",
    ),
)

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

ALL: tuple[Sample, ...] = (ACA, ERISA, MANGLED, UNRELATED)
