"""The letter, and the one thing it will not write."""

from __future__ import annotations

from datetime import date

import pytest

from recourse.domain.appeal import Assertion, Deadlines
from recourse.domain.models import Claim, ClaimLine, Denial, Plan
from recourse.domain.money import Money
from recourse.domain.packet import UncitedAssertion, build_letter_body
from recourse.domain.types import AppealStage, DenialClass, PlanType, ServiceType

PLAN = Plan(
    plan_id="p1", name="Meridian Silver 4000", plan_type=PlanType.ACA_MARKETPLACE,
    member_id="MB-4417093",
)
LINE = ClaimLine(
    line_id="l1", claim_id="c1", description="MRI, lumbar spine, without contrast",
    service_date=date(2026, 6, 11), provider="Northgate Imaging",
    billed=Money.from_dollars("2410.00"), allowed=Money.from_dollars("1180.00"),
    plan_paid=Money.zero(), patient_responsibility=Money.from_dollars("1180.00"),
    carc=("197",),
)
CLAIM = Claim(
    claim_id="c1", plan_id="p1", provider="Northgate Imaging",
    service_type=ServiceType.POST_SERVICE, notice_date=date(2026, 6, 28), lines=(LINE,),
)
DENIAL = Denial(
    denial_id="d1", claim_id="c1", line_id="l1", denial_class=DenialClass.AUTHORIZATION,
    matched_code="197",
    reason_text="Precertification/authorization/notification/pre-treatment absent.",
)
DEADLINES = Deadlines(
    stage=AppealStage.INTERNAL_1, mine=date(2026, 12, 25), theirs=date(2026, 8, 27),
    next_stage=AppealStage.EXTERNAL, next_stage_window_days=120,
    basis="29 CFR 2560.503-1", citation="60 days for a post-service appeal",
)


def _build(assertions, **kw):
    return build_letter_body(
        claim=CLAIM, line=LINE, denial=DENIAL, plan=PLAN, deadlines=DEADLINES,
        assertions=assertions, **kw,
    )


def test_the_letter_names_the_code_it_contests_and_the_money_at_stake():
    body = _build((Assertion("The authorisation was obtained on 2 June 2026."),))
    assert "CARC 197" in body.text
    assert "Precertification" in body.text
    assert "$1180.00" in body.text
    assert "MB-4417093" in body.text


def test_a_clinical_assertion_with_no_document_is_refused():
    """Not a weak appeal — a false statement on an insurance document, in the
    patient's name. The function raises rather than writing it."""
    with pytest.raises(UncitedAssertion) as caught:
        _build((Assertion("The patient has had these symptoms since March.",
                          clinical=True),))
    assert "symptoms since March" in str(caught.value)


def test_the_same_assertion_with_a_document_behind_it_is_written_and_traced():
    body = _build((Assertion("The patient has had these symptoms since March.",
                             clinical=True, document_id="doc-note-7"),))
    assert "symptoms since March" in body.text
    assert body.citations == (
        ("The patient has had these symptoms since March.", "doc-note-7"),
    )


def test_a_non_clinical_sentence_needs_no_citation():
    """A claim number, a date and an amount are facts of the record itself."""
    body = _build((Assertion("This claim was submitted on 14 June 2026."),))
    assert body.citations == ()
    assert "14 June 2026" in body.text


def test_the_letter_states_the_insurers_own_deadline_back_to_it():
    """The clock the insurer owes the claimant is the one nobody else is counting."""
    body = _build((Assertion("The authorisation was obtained."),))
    assert "27 August 2026" in body.text
    assert "29 CFR 2560.503-1" in body.text


def test_a_deadline_that_has_not_started_produces_no_sentence_about_it():
    """A two-level appeal whose first level is unanswered has no second-level date.
    Saying nothing is right; inventing a date is not."""
    unstarted = Deadlines(
        stage=AppealStage.INTERNAL_2, mine=None, theirs=None,
        next_stage=None, next_stage_window_days=None,
    )
    body = build_letter_body(
        claim=CLAIM, line=LINE, denial=DENIAL, plan=PLAN, deadlines=unstarted,
        assertions=(Assertion("The authorisation was obtained."),),
    )
    assert "due by" not in body.text


def test_attachments_are_listed_where_given():
    body = _build((Assertion("See the attached approval."),),
                  attachments=("Authorisation letter, 2 June 2026",))
    assert "Authorisation letter, 2 June 2026" in body.text
    assert body.attachments == ("Authorisation letter, 2 June 2026",)


def test_the_same_input_always_produces_the_same_letter():
    """A draft a person can check, rather than one they must re-read each time."""
    assertions = (Assertion("The authorisation was obtained on 2 June 2026."),)
    assert _build(assertions).text == _build(assertions).text
