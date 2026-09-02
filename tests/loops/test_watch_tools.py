"""What the WATCH tools do, and what they refuse.

The two that matter most are the CARC 50 refusal and the CARC 16 draft. They are the
demo, and they are the line the product draws: one denial is a form problem the agent
can prepare unaided, and the other is the treating clinician's argument.
"""

from __future__ import annotations

from recourse.domain.types import DenialClass
from tests.loops.support import watch

_CLERICAL = [{"text": "The claim omitted the rendering provider identifier.",
              "clinical": False}]


def test_the_clinical_denial_is_refused_because_no_clinician_has_written_anything():
    """CARC 50 with no letter of medical necessity. An error dict, never a draft."""
    store, tools, _ = watch()
    result = tools["draft_letter_body"](
        denial_id="den-50",
        assertions=[{"text": "The visits were medically necessary.", "clinical": True,
                     "document_id": "doc-eob-homehealth"}],
    )
    assert "error" in result
    assert "clinical_note" in result["error"]
    assert store.appeal("appeal-50").letter_body == ""


def test_an_uncited_clinical_sentence_comes_back_as_a_refusal_not_a_crash():
    """`UncitedAssertion` is a raise in the domain and an {"error": ...} here.

    A traceback out of a tool ends the run with no record of what it tried to write;
    a refusal is something the model can read and act on.
    """
    store, tools, _ = watch()
    result = tools["draft_letter_body"](
        denial_id="den-197",
        assertions=[{"text": "The scan was medically indicated.", "clinical": True}],
    )
    assert "error" in result
    assert "no document" in result["error"]
    assert store.appeal("appeal-197").letter_body == ""


def test_the_clerical_denial_drafts_and_the_letter_lands_on_the_appeal():
    store, tools, _ = watch()
    result = tools["draft_letter_body"](denial_id="den-16", assertions=_CLERICAL)
    assert "error" not in result
    appeal = store.appeal(result["appeal_id"])
    assert appeal.letter_body
    assert "CARC 16" in appeal.letter_body
    assert appeal.assertions[0].text == _CLERICAL[0]["text"]


def test_explain_denial_reads_the_class_from_the_code_and_the_dates_from_the_clocks():
    _, tools, _ = watch()
    explained = tools["explain_denial"](denial_id="den-50")
    assert explained["carc"] == "50"
    assert explained["denial_class"] == DenialClass.CLINICAL.value
    # Day 150 of 180 against the frozen clock, and the citation travels with it.
    assert explained["days_remaining"] == 30
    assert explained["citation"].startswith("https://")


def test_an_invented_denial_id_is_refused_rather_than_answered():
    _, tools, _ = watch()
    for name in ("explain_denial", "check_evidence"):
        assert "error" in tools[name](denial_id="den-does-not-exist")


def test_a_document_this_class_does_not_need_is_refused_and_names_what_would_do():
    _, tools, requests = watch()
    result = tools["request_document"](denial_id="den-197", kind="pay_stub",
                                       from_whom="Northgate Imaging")
    assert "error" in result and "authorization" in result["error"]
    assert requests == []


def test_a_document_the_class_does_need_is_asked_for_and_recorded():
    _, tools, requests = watch()
    result = tools["request_document"](denial_id="den-50", kind="clinical_note",
                                       from_whom="Dr Adeyemi, St. Brendan's")
    assert result["requested"] is True
    assert requests[0]["kind"] == "clinical_note"
