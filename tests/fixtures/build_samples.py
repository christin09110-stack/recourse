"""Generate the sample EOB PDFs the ingest tests parse.

Run: ``python tests/fixtures/build_samples.py``. Output is deterministic, and the
PDFs are committed, so the test suite never depends on regenerating them (or on
``reportlab`` being installed at all — it is a dev-only dependency).

The insurers, members, providers and claim numbers are invented. The *shape* is
not: labelled header block, a fixed-width service table, a totals row, and a
reason-code legend underneath, which is how a consumer EOB actually reads.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from reportlab import rl_config
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))
from samples_data import ACA, ERISA, Sample  # noqa: E402
from samples_edge import ALL as EDGE  # noqa: E402

HERE = Path(__file__).resolve().parent
ROW = "{date:<10} {proc:<6} {desc:<32} {billed:>10} {allowed:>10} {paid:>10} {resp:>10}  {codes}"
HEADINGS = ROW.format(
    date="SERVICE", proc="PROC", desc="DESCRIPTION OF SERVICE", billed="BILLED",
    allowed="ALLOWED", paid="PLAN PAID", resp="YOU OWE", codes="REASON CODES",
)


def _draw(canvas: Canvas, sample: Sample) -> None:
    y = 740.0

    def line(text: str, font: str = "Courier", size: float = 7.6, drop: float = 11.0) -> None:
        nonlocal y
        canvas.setFont(font, size)
        canvas.drawString(48, y, text)
        y -= drop

    line(sample.insurer, "Helvetica-Bold", 15, 20)
    line(sample.subtitle, "Helvetica", 9, 22)
    for label, value in sample.header:
        line(f"{label:<16} {value}", "Helvetica", 9)
    if not sample.rows:
        _draw_notes(line, sample)
        return
    y -= 12
    line(HEADINGS, "Courier-Bold", 7.6)
    line("-" * len(HEADINGS))
    for row in sample.rows:
        line(ROW.format(**row))
    line("-" * len(HEADINGS))
    line(ROW.format(
        date="TOTALS", proc="", desc="", billed=sample.totals[0], allowed=sample.totals[1],
        paid=sample.totals[2], resp=sample.totals[3], codes="",
    ), "Courier-Bold")
    _draw_notes(line, sample)


def _draw_notes(line: Callable[..., None], sample: Sample) -> None:
    if sample.rows:
        line("", "Helvetica", 9, 16)
        line("WHY WE DID NOT PAY SOME OF THESE CHARGES", "Helvetica-Bold", 9, 14)
    for note in sample.legend:
        line(note, "Helvetica", 8.5, 12)
    line("", "Helvetica", 8, 8)
    for note in sample.rights:
        line(note, "Helvetica-Oblique", 8, 11)


def build(sample: Sample) -> Path:
    """Write one sample PDF and return its path.

    `invariant` freezes the creation timestamp and document id, so regenerating
    gives byte-identical files and a rebuild shows up in git only when the content
    really changed.
    """
    rl_config.invariant = 1
    path = HERE / sample.filename
    canvas = Canvas(str(path), pagesize=LETTER)
    canvas.setTitle(sample.insurer)
    _draw(canvas, sample)
    canvas.showPage()
    canvas.save()
    return path


def main() -> None:
    for sample in (ACA, ERISA, *EDGE):
        print(build(sample))


if __name__ == "__main__":
    main()
