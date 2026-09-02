"""How the guard reads what it is given, and when it reads it."""

from datetime import date

from strands.interventions.actions import Deny, Proceed

from recourse.domain.appeal import Appeal, Assertion
from recourse.domain.models import Document
from recourse.domain.types import AppealStage
from recourse.policy.citation import CitationGuard
from tests.policy.support import case_with, guard_over, said, tool_event


def test_a_clinical_flag_arriving_as_a_json_string_still_counts_as_clinical():
    """A model that sends "true" rather than true must not thereby skip the check."""
    guard = guard_over(case_with())
    action = guard.before_tool_call(
        tool_event("draft_letter_body", assertions=[said("Necessary.", clinical="true")]))
    assert isinstance(action, Deny)


def test_an_assertion_this_guard_cannot_read_is_denied_rather_than_waved_through():
    """Unknown is never benign: an unread claim is not a checked one."""
    guard = guard_over(case_with("doc-1"))
    action = guard.before_tool_call(
        tool_event("draft_letter_body", assertions=["a bare string"]))
    assert isinstance(action, Deny)


def test_sealing_a_draft_rechecks_the_assertions_already_stored_on_the_appeal():
    """Drafting and sending are two calls; the second must not skip the first's guard."""
    appeal = Appeal.opened(
        appeal_id="ap-1", denial_id="dn-1", plan_id="pl-1", stage=AppealStage.INTERNAL_1,
        assertions=(Assertion(text="The infusion was necessary.", clinical=True),),
    )
    guard = guard_over(case_with("doc-1", appeals=(appeal,)))
    assert isinstance(
        guard.before_tool_call(tool_event("mark_ready_to_send", appeal_id="ap-1")), Deny)


def test_sealing_a_draft_whose_assertions_are_all_cited_proceeds():
    appeal = Appeal.opened(
        appeal_id="ap-1", denial_id="dn-1", plan_id="pl-1", stage=AppealStage.INTERNAL_1,
        assertions=(Assertion(text="The scan showed progression.", clinical=True,
                              document_id="doc-1"),),
    )
    guard = guard_over(case_with("doc-1", appeals=(appeal,)))
    assert isinstance(
        guard.before_tool_call(tool_event("mark_ready_to_send", appeal_id="ap-1")), Proceed)


def test_the_guard_reads_the_case_file_now_rather_than_when_it_was_built():
    """Documents arrive mid-run; a snapshot would refuse support that landed a call ago."""
    case = case_with()
    guard = guard_over(case)
    call = tool_event("draft_letter_body",
                      assertions=[said("Necessary.", document_id="doc-7")])
    assert isinstance(guard.before_tool_call(call), Deny)

    case.documents["doc-7"] = Document(
        document_id="doc-7", kind="clinical_note", title="LMN", received_on=date(2026, 3, 2))
    assert isinstance(guard.before_tool_call(call), Proceed)


def test_an_unlisted_tool_carrying_assertions_is_still_checked():
    """Found by shape, so a letter-writing tool added later cannot slip past a list."""
    guard = guard_over(case_with())
    assert isinstance(guard.before_tool_call(
        tool_event("some_new_packet_tool", assertions=[said("Necessary.")])), Deny)


def test_before_tool_call_is_defined_on_the_class_not_the_instance():
    """Strands inspects the class; an instance attribute silently disables the guard."""
    assert "before_tool_call" in CitationGuard.__dict__
