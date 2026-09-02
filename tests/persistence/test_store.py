from datetime import date

import pytest

from recourse.domain.appeal import Appeal, Assertion
from recourse.domain.case import CaseFile
from recourse.domain.models import Document
from recourse.domain.types import AppealStage, Outcome
from recourse.persistence.store import CaseStore


def _store(appeal: Appeal | None = None) -> CaseStore:
    case = CaseFile(case_id="case-1")
    if appeal is not None:
        case.appeals[appeal.appeal_id] = appeal
    return CaseStore(case)


def _appeal(**kw) -> Appeal:
    return Appeal.opened(
        appeal_id="app-1", denial_id="den-1", plan_id="plan-1",
        stage=AppealStage.INTERNAL_1, started_on=date(2026, 3, 1), **kw,
    )


def test_advancing_a_stage_keeps_the_earlier_appeal_in_history():
    store = _store(_appeal(letter_body="We contest CARC 197."))
    store.record_response("app-1", Outcome.UPHELD, date(2026, 4, 10))
    store.advance_stage("app-1", AppealStage.INTERNAL_2, date(2026, 4, 10))

    now = store.appeal("app-1")
    assert now.stage is AppealStage.INTERNAL_2
    assert now.outcome is Outcome.PENDING and now.letter_body == ""

    # The level-one decision is the thing level two argues against.
    # One record per level, holding everything that happened at it - rather than
    # two snapshots of the whole appeal taken by whatever mutated it.
    history = store.history("app-1")
    assert [h.stage for h in history] == [AppealStage.INTERNAL_1]
    assert history[0].outcome is Outcome.UPHELD
    assert history[0].answered_on == date(2026, 4, 10)
    assert history[0].letter_body == "We contest CARC 197."


def test_recording_a_response_without_a_date_is_refused():
    # An answer with no date reads downstream as "this stage never began", so the
    # next level can never compute a deadline and nothing ever complains.
    store = _store(_appeal())
    with pytest.raises(ValueError, match="date"):
        store.record_response("app-1", Outcome.UPHELD, None)
    assert store.appeal("app-1").outcome is Outcome.PENDING


def test_recording_pending_as_an_answer_is_refused():
    store = _store(_appeal())
    with pytest.raises(ValueError, match="not an answer"):
        store.record_response("app-1", Outcome.PENDING, date(2026, 4, 10))


def test_advancing_an_unanswered_appeal_is_refused():
    # Level two's clock starts when level one is answered. Advancing now would
    # stamp a start date on a clock that has not started.
    store = _store(_appeal())
    with pytest.raises(ValueError, match="invent a deadline"):
        store.advance_stage("app-1", AppealStage.INTERNAL_2, date(2026, 4, 10))
    assert store.appeal("app-1").stage is AppealStage.INTERNAL_1
    assert store.history("app-1") == ()


def test_a_document_added_is_visible_through_documents_of_kind():
    store = _store()
    store.add_document(Document(
        document_id="doc-1", kind="authorization",
        title="Prior authorisation approval", received_on=date(2026, 2, 2),
    ))
    found = store.case.documents_of_kind("authorization")
    assert [d.document_id for d in found] == ["doc-1"]
    assert store.case.documents_of_kind("clinical_note") == ()


def test_a_letter_is_attached_without_being_sent():
    store = _store(_appeal())
    store.attach_letter("app-1", "Body.", [Assertion(text="Claim 9.", clinical=False)])
    assert store.appeal("app-1").sent_on is None
    store.mark_sent("app-1", date(2026, 3, 20))
    assert store.appeal("app-1").sent_on == date(2026, 3, 20)


def test_sending_an_appeal_with_no_letter_is_refused():
    store = _store(_appeal())
    with pytest.raises(ValueError, match="no letter to send"):
        store.mark_sent("app-1", date(2026, 3, 20))


def test_reopening_a_live_appeal_id_raises():
    store = _store(_appeal())
    with pytest.raises(KeyError, match="already open"):
        store.open_appeal(_appeal())
