"""The journal: what happened, when, and who decided it.

`GET /api/journal.csv` is not a convenience. An appeal is an argument with an
institution that keeps its own record, and the claimant's account is worth something
only if it was written as things happened and can be handed to somebody — an
ombudsman, an appeals unit, or the person themselves eight months later — as a file
they can open rather than an API they have to call.

Read-only, both of them. The journal is append-only and nothing over HTTP may edit
or remove an entry: a log that can be quietly corrected is not evidence of anything.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import Response

from recourse.api.state import RecourseState


def add_journal_routes(app: FastAPI) -> None:
    @app.get("/api/journal")
    def get_journal() -> list[dict[str, Any]]:
        """Everything written, oldest first."""
        state: RecourseState = app.state.recourse
        return [
            {
                "at": entry.at.isoformat(),
                "kind": entry.kind,
                "sentence": entry.sentence,
                "appeal_id": entry.appeal_id,
                "document_id": entry.document_id,
                # Empty where the agent acted alone, which is itself worth seeing.
                "decided_by": entry.decided_by,
            }
            for entry in state.journal.entries()
        ]

    @app.get("/api/journal.csv")
    def get_journal_csv() -> Response:
        """The export somebody actually files. Same rows, same order."""
        state: RecourseState = app.state.recourse
        return Response(
            content=state.journal.to_csv(),
            media_type="text/csv",
            headers={"content-disposition": "attachment; filename=journal.csv"},
        )
