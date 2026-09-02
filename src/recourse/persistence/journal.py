"""What happened, when, and who decided it.

Append-only, and that is the whole design. An appeal is an argument with an
institution that keeps its own record, and the person's account of it is worth
something only if it was written as things happened rather than assembled afterwards
from memory. So this class exposes `write` and two readers, and nothing that edits
or removes an entry — not because deletion is unlikely to be wanted, but because a
log you can quietly correct is not evidence of anything.

`to_csv` exists for the same reason. An investigator, an ombudsman, or the person
themselves eight months later needs a file they can open, not an API.

In memory, deliberately: this build has no durable store, and pretending otherwise
would be worse than admitting it. The journal dies with the process.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone

_COLUMNS = ("at", "kind", "sentence", "appeal_id", "document_id", "decided_by")


@dataclass(frozen=True)
class JournalEntry:
    """One thing that happened, in a sentence a person can read."""

    at: datetime
    kind: str
    #: Plain English, not a template key. This is the column somebody actually reads.
    sentence: str
    appeal_id: str | None = None
    document_id: str | None = None
    #: Empty when the agent acted alone — which is itself worth being able to see.
    decided_by: str = ""

    def as_row(self) -> list[str]:
        return [
            self.at.isoformat(), self.kind, self.sentence,
            self.appeal_id or "", self.document_id or "", self.decided_by,
        ]


class Journal:
    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def write(
        self,
        *,
        kind: str,
        sentence: str,
        at: datetime | None = None,
        appeal_id: str | None = None,
        document_id: str | None = None,
        decided_by: str = "",
    ) -> JournalEntry:
        """Append one entry and return it. The only way to change this journal.

        `at` is a parameter rather than always `now` because the demo world runs on
        a frozen clock; a journal that stamped wall-clock time would disagree with
        every deadline on the screen beside it.
        """
        entry = JournalEntry(
            at=at or datetime.now(timezone.utc), kind=kind, sentence=sentence,
            appeal_id=appeal_id, document_id=document_id, decided_by=decided_by,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> tuple[JournalEntry, ...]:
        """Everything written, oldest first.

        A tuple, not the list: handing out the internal list would let a caller
        append, reorder or clear the record through the back door, which is exactly
        the thing this store promises cannot happen.
        """
        return tuple(self._entries)

    def to_csv(self) -> str:
        """The export an investigator asks for."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(_COLUMNS)
        for entry in self._entries:
            writer.writerow(entry.as_row())
        return out.getvalue()
