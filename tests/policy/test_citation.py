from strands.interventions.actions import Confirm, Deny, Proceed

from recourse.domain.appeal import Assertion
from tests.policy.support import case_with, guard_over, said, tool_event


def test_an_uncited_clinical_assertion_is_denied_and_never_offered_for_approval():
    """There is nothing to approve about a sentence the record does not support.

    A Confirm here would invite someone, mid-triage and unwell, to wave through a
    false statement on an insurance document made in a patient's name.
    """
    guard = guard_over(case_with("doc-1"))
    action = guard.before_tool_call(tool_event(
        "draft_letter_body",
        assertions=[said("The infusion was medically necessary.")],
    ))
    assert isinstance(action, Deny)
    assert not isinstance(action, Confirm)
    assert "medically necessary" in action.reason


def test_a_clinical_assertion_citing_a_document_not_in_the_file_is_denied():
    guard = guard_over(case_with("doc-1"))
    action = guard.before_tool_call(tool_event(
        "draft_letter_body",
        assertions=[said("Dr Ahenkorah recorded worsening dyspnoea.", document_id="doc-9")],
    ))
    assert isinstance(action, Deny)
    assert "doc-9" in action.reason


def test_a_clinical_assertion_citing_a_real_document_proceeds():
    guard = guard_over(case_with("doc-1"))
    action = guard.before_tool_call(tool_event(
        "draft_letter_body",
        assertions=[said("Dr Ahenkorah recorded worsening dyspnoea.", document_id="doc-1")],
    ))
    assert isinstance(action, Proceed)


def test_a_non_clinical_assertion_needs_no_citation():
    """A claim number, a date, an amount in dispute: facts of the record itself."""
    guard = guard_over(case_with())
    action = guard.before_tool_call(tool_event(
        "draft_letter_body",
        assertions=[said("Claim CLM-4471 was denied on 12 March 2026 under CARC 50.",
                         clinical=False)],
    ))
    assert isinstance(action, Proceed)


def test_a_tool_call_carrying_no_assertions_proceeds():
    assert isinstance(
        guard_over(case_with()).before_tool_call(tool_event("list_denials")), Proceed)


def test_one_uncited_sentence_condemns_a_packet_whose_others_are_cited():
    guard = guard_over(case_with("doc-1"))
    action = guard.before_tool_call(tool_event(
        "draft_letter_body",
        assertions=[
            said("Claim CLM-4471 was denied under CARC 50.", clinical=False),
            said("The scan showed progression.", document_id="doc-1"),
            said("The patient's condition is deteriorating."),
        ],
    ))
    assert isinstance(action, Deny)
    assert "deteriorating" in action.reason


def test_assertion_objects_are_checked_as_well_as_the_dicts_a_model_sends():
    guard = guard_over(case_with("doc-1"))
    uncited = Assertion(text="The scan showed progression.", clinical=True)
    assert isinstance(
        guard.before_tool_call(tool_event("draft_letter_body", assertions=[uncited])), Deny)


def test_the_refusal_is_recorded_so_the_console_can_say_what_was_refused():
    guard = guard_over(case_with())
    guard.before_tool_call(
        tool_event("draft_letter_body", assertions=[said("Necessary.")]))
    assert len(guard.refusals) == 1
