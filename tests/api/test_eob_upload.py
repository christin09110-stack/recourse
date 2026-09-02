"""Uploading an EOB, including one that is not an EOB.

The route must never 500. The person uploading is holding a letter they do not
understand, and a stack trace is indistinguishable from "there is nothing wrong with
your claim" — which is the single most expensive thing this product could say.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _upload(client, name: str, data: bytes):
    return client.post("/api/eob", files={"file": (name, data, "application/pdf")})


def test_the_good_sample_comes_back_as_its_lines(client):
    response = _upload(client, "eob.pdf", (FIXTURES / "sample-aca-eob.pdf").read_bytes())
    assert response.status_code == 200
    body = response.json()

    assert len(body["lines"]) == 6
    assert body["claim_id"] == "2026-CLM-8841203"
    assert body["notice_date"] == "2026-03-04"
    assert body["warnings"] == []
    assert body["needs_review"] is False
    # Classified on the way out by the same engine the loops use, so the upload
    # screen and the triage screen cannot disagree about what CARC 50 is.
    assert [d["denial_class"] for d in body["denied"]] == ["clerical", "clinical"]


def test_a_damaged_eob_reports_flagged_lines_rather_than_dropping_them(client):
    response = _upload(client, "eob.pdf", (FIXTURES / "sample-mangled-eob.pdf").read_bytes())
    assert response.status_code == 200
    body = response.json()
    assert body["flagged"], "a row that could not be read must be flagged, never dropped"
    assert body["needs_review"] is True
    assert any("could not be fully read" in w for w in body["warnings"])


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("garbage.pdf", b"this is not a pdf at all"),
        ("empty.pdf", b""),
        ("truncated.pdf", b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog"),
    ],
)
def test_rubbish_is_an_answer_never_a_500(client, name, data):
    response = _upload(client, name, data)
    assert response.status_code == 200
    body = response.json()
    # Either nothing was read or what was read is flagged. Never a silent success.
    assert body["lines"] == [] or body["flagged"]
    assert body["warnings"], "a file that could not be read must say so"
    assert body["needs_review"] is True


def test_a_pdf_that_is_not_an_eob_says_so(client):
    body = _upload(client, "letter.pdf",
                   (FIXTURES / "sample-unrelated.pdf").read_bytes()).json()
    assert body["lines"] == []
    assert any("may not be an EOB" in w or "no text" in w for w in body["warnings"])


def test_the_upload_is_written_into_the_journal(client):
    _upload(client, "eob.pdf", (FIXTURES / "sample-aca-eob.pdf").read_bytes())
    kinds = [entry["kind"] for entry in client.get("/api/journal").json()]
    assert "eob_uploaded" in kinds
