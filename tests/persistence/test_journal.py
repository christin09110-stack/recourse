import csv
import io
from datetime import datetime, timezone

from recourse.persistence.journal import Journal

_AT = datetime(2026, 4, 10, 9, 30, tzinfo=timezone.utc)


def _journal() -> Journal:
    journal = Journal()
    journal.write(
        kind="denial_classified", at=_AT,
        sentence="CARC 197 on line 3 is an authorization denial; the approval is on file.",
        appeal_id="app-1", document_id="doc-1",
    )
    journal.write(
        kind="decision_answered", at=_AT,
        sentence="Ana Okafor approved sending the level-one appeal.",
        appeal_id="app-1", decided_by="Ana Okafor",
    )
    return journal


def test_entries_come_back_oldest_first_as_a_tuple_nobody_can_append_to():
    journal = _journal()
    assert isinstance(journal.entries(), tuple)
    assert [e.kind for e in journal.entries()] == ["denial_classified", "decision_answered"]


def test_the_journal_exposes_no_way_to_edit_or_remove_an_entry():
    # A log you can quietly correct is not evidence of anything, so append is the
    # only public verb. `entries()` hands out a copy for the same reason.
    journal = _journal()
    public = {name for name in dir(journal) if not name.startswith("_")}
    assert public == {"write", "entries", "to_csv"}
    journal.entries()  # a tuple: no append, no clear, no reordering
    assert len(journal.entries()) == 2


def test_to_csv_round_trips_every_row():
    journal = _journal()
    rows = list(csv.DictReader(io.StringIO(journal.to_csv())))
    assert [r["kind"] for r in rows] == ["denial_classified", "decision_answered"]
    assert rows[0]["at"] == _AT.isoformat()
    assert rows[0]["document_id"] == "doc-1"
    assert rows[0]["decided_by"] == ""       # the agent acted alone, and it shows
    assert rows[1]["decided_by"] == "Ana Okafor"
    assert rows[1]["document_id"] == ""
    assert rows[1]["sentence"] == "Ana Okafor approved sending the level-one appeal."
    assert all(r["appeal_id"] == "app-1" for r in rows)


def test_an_entry_written_without_a_time_is_still_stamped():
    entry = Journal().write(kind="note", sentence="Uploaded the EOB.")
    assert entry.at.tzinfo is not None
