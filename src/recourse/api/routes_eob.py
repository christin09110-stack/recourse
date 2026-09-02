"""Uploading an Explanation of Benefits.

This route cannot return a 500. The person on the other end of it is holding a
letter they do not understand, and an error page is indistinguishable from "there is
nothing wrong with your claim". `parse_eob` is total by construction; the belt here
is for everything around it — a truncated multipart body, an unreadable stream — so
that a bad file comes back as a document with warnings rather than as a stack trace.

What it will not do is invent. A file it could not read comes back with no lines and
a warning saying so, and a row it could not read comes back flagged. Both are
reported; neither is silence. A silently dropped denial is the failure this product
exists to prevent.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, UploadFile

from recourse.api.serialise import line_view
from recourse.api.state import RecourseState
from recourse.domain.codes import classify
from recourse.ingest import ParsedEOB, parse_eob


def _denied_view(parsed: ParsedEOB) -> list[dict[str, Any]]:
    """The refused lines, each classified by the same engine the loops use."""
    out = []
    for line in parsed.denied:
        found = classify(line.carc, line.rarc)
        out.append({
            "line_id": line.line_id,
            "carc": list(line.carc),
            "rarc": list(line.rarc),
            "denial_class": found.denial_class.value,
            "matched_code": found.matched.code if found.matched else "",
            "reason": found.reason,
        })
    return out


def _parsed_view(parsed: ParsedEOB) -> dict[str, Any]:
    return {
        "plan_name": parsed.plan_name,
        "member_id": parsed.member_id,
        "claim_id": parsed.claim_id,
        "notice_date": parsed.notice_date.isoformat() if parsed.notice_date else None,
        "provider": parsed.provider,
        "lines": [line_view(line) for line in parsed.lines],
        "denied": _denied_view(parsed),
        "flagged": [line_view(line) for line in parsed.flagged],
        "warnings": list(parsed.warnings),
        "needs_review": parsed.needs_review,
    }


def add_eob_routes(app: FastAPI) -> None:
    @app.post("/api/eob")
    async def post_eob(file: UploadFile = File(...)) -> dict[str, Any]:
        """Read an uploaded EOB. Reports what it read and what it could not."""
        state: RecourseState = app.state.recourse
        try:
            parsed = parse_eob(await file.read())
        except Exception as exc:  # noqa: BLE001 - see the module docstring
            # Deliberately broad. Whatever went wrong, the answer to the person is
            # the same shape as any other unreadable document, and it is never a 500.
            parsed = ParsedEOB(warnings=(f"this file could not be read: {exc}",))

        state.journal.write(
            kind="eob_uploaded",
            sentence=(
                f"An EOB was uploaded: {len(parsed.lines)} service lines read, "
                f"{len(parsed.denied)} of them denied, {len(parsed.flagged)} flagged "
                "for a person to check."
            ),
            at=state.world.now_at(),
        )
        return _parsed_view(parsed)
