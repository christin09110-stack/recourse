"""The case file, and the only place allowed to change it.

In memory, deliberately: this build has no durable store, and pretending otherwise
would be worse than admitting it. Restart the process and the whole case file — the
documents, the denials, every appeal and its history — is gone.

Everything in `domain/` is frozen, so changing an appeal means building its
replacement and reseating it. That happens in one method (`_reseat`), so no caller
can build a new appeal and forget to file it, and the version being replaced is kept
first: an appeal that advances to level two must not lose the level-one decision it
is appealing against. The guards on those moves live in `moves.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from recourse.domain.appeal import Appeal, Assertion
from recourse.domain.case import CaseFile
from recourse.domain.models import Denial, Document
from recourse.domain.types import AppealStage, Outcome
from recourse.persistence.moves import advanced, lettered, responded, sent


class CaseStore:
    """Holds one household's case file and applies every change to it."""

    def __init__(self, case_file: CaseFile) -> None:
        self._case = case_file

    @property
    def case(self) -> CaseFile:
        return self._case

    def add_document(self, document: Document) -> Document:
        """File a document, visible at once to `CaseFile.documents_of_kind` — which
        is what `evidence.gaps` reads. A document that arrives and does not close
        its gap is, to the person chasing it, a document that never arrived."""
        self._case.documents[document.document_id] = document
        return document

    def add_denial(self, denial: Denial) -> Denial:
        self._case.denials[denial.denial_id] = denial
        return denial

    def open_appeal(self, appeal: Appeal) -> Appeal:
        # Re-opening a live id would drop its stage, its clock and its letter on the
        # floor without a word. Muster's inbox learned this one in production.
        if appeal.appeal_id in self._case.appeals:
            raise KeyError(f"appeal {appeal.appeal_id!r} is already open")
        self._case.appeals[appeal.appeal_id] = appeal
        return appeal

    def appeal(self, appeal_id: str) -> Appeal:
        appeal = self._case.appeals.get(appeal_id)
        if appeal is None:
            raise KeyError(f"no appeal {appeal_id!r}")
        return appeal

    def history(self, appeal_id: str) -> tuple:
        """The levels this appeal has already been through, oldest first.

        Read off the appeal itself. It used to be a list the store kept beside it,
        which meant an appeal serialised for the API arrived without the history the
        API most needed to show.
        """
        return self.appeal(appeal_id).history

    def record_response(self, appeal_id: str, outcome: Outcome, answered_on: date) -> Appeal:
        """Record what the insurer said and the date it said it. See `moves.responded`."""
        return self._reseat(responded(self.appeal(appeal_id), outcome, answered_on))

    def advance_stage(self, appeal_id: str, to_stage: AppealStage, started_on: date) -> Appeal:
        """Carry this appeal to the next stage. See `moves.advanced`."""
        return self._reseat(advanced(self.appeal(appeal_id), to_stage, started_on))

    def attach_letter(
        self, appeal_id: str, body: str, assertions: Sequence[Assertion] = ()
    ) -> Appeal:
        """Attach a drafted letter body. Drafting is not sending: `sent_on` stays
        unset, and only a person calls `mark_sent`."""
        return self._reseat(
            lettered(self.appeal(appeal_id), body, tuple(assertions))
        )

    def mark_sent(self, appeal_id: str, on: date) -> Appeal:
        """Record that a person sent it. Nothing here sends anything."""
        return self._reseat(sent(self.appeal(appeal_id), on))

    def _reseat(self, updated: Appeal) -> Appeal:
        self._case.appeals[updated.appeal_id] = updated
        return updated
