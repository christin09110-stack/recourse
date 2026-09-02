"""What a credible appeal needs, and what the file is missing."""

from __future__ import annotations

from datetime import date

import pytest

from recourse.domain.case import CaseFile
from recourse.domain.evidence import can_prepare_alone, gaps, requirements_for
from recourse.domain.models import Document
from recourse.domain.types import DenialClass


def case_with(*kinds: str) -> CaseFile:
    """A case file holding one document of each named kind, and nothing else."""
    documents = {
        f"doc-{i}": Document(
            document_id=f"doc-{i}",
            kind=kind,
            title=f"{kind} on file",
            received_on=date(2026, 3, 1),
        )
        for i, kind in enumerate(kinds)
    }
    return CaseFile(case_id="case-1", documents=documents)


def test_clinical_denial_without_a_clinician_letter_reports_that_gap() -> None:
    missing = gaps(case_with("eob", "denial_letter"), DenialClass.CLINICAL)

    assert [req.kind for req in missing] == ["clinical_note"]


def test_clerical_denial_with_the_eob_alone_has_no_gaps() -> None:
    # The corrected claim detail is the provider's biller's to issue; requiring it
    # would park a fixable denial behind a document the patient cannot produce.
    assert gaps(case_with("eob"), DenialClass.CLERICAL) == ()
    assert can_prepare_alone(case_with("eob"), DenialClass.CLERICAL)


def test_authorization_denial_whose_approval_is_already_on_file_has_no_gaps() -> None:
    # The demo's second denial: CARC 197, and the approval letter was in the file
    # the whole time. If this reports a gap the agent asks for what it already has.
    case_file = case_with("eob", "authorization")

    assert gaps(case_file, DenialClass.AUTHORIZATION) == ()
    assert can_prepare_alone(case_file, DenialClass.AUTHORIZATION)


def test_authorization_denial_without_the_approval_reports_the_gap() -> None:
    assert [r.kind for r in gaps(case_with("eob"), DenialClass.AUTHORIZATION)] == ["authorization"]


def test_unassessable_yields_no_requirements() -> None:
    assert requirements_for(DenialClass.UNASSESSABLE) == ()
    assert gaps(case_with("eob"), DenialClass.UNASSESSABLE) == ()


def test_unassessable_is_never_preparable_alone_despite_having_no_gaps() -> None:
    # An empty requirement list is the absence of a reason, not a clean bill.
    assert not can_prepare_alone(case_with("eob"), DenialClass.UNASSESSABLE)


def test_clinical_is_never_preparable_alone_even_with_the_letter_present() -> None:
    case_file = case_with("eob", "clinical_note")

    assert gaps(case_file, DenialClass.CLINICAL) == ()
    assert not can_prepare_alone(case_file, DenialClass.CLINICAL)


@pytest.mark.parametrize("denial_class", list(DenialClass))
def test_every_requirement_explains_what_it_establishes(denial_class: DenialClass) -> None:
    for req in requirements_for(denial_class):
        assert req.why.strip(), f"{denial_class.value}/{req.kind} has no why"


def test_timeliness_says_the_patient_may_not_be_liable() -> None:
    why = " ".join(req.why for req in requirements_for(DenialClass.TIMELINESS))

    assert "provider" in why and "liable" in why


ASSESSABLE = [c for c in DenialClass if c is not DenialClass.UNASSESSABLE]


@pytest.mark.parametrize("denial_class", ASSESSABLE)
def test_every_assessable_class_has_a_required_document(denial_class: DenialClass) -> None:
    assert any(req.required for req in requirements_for(denial_class))


def test_an_empty_case_file_gaps_everything_required() -> None:
    empty = CaseFile(case_id="case-empty")

    for denial_class in (DenialClass.ELIGIBILITY, DenialClass.COVERAGE, DenialClass.TIMELINESS):
        required = [req for req in requirements_for(denial_class) if req.required]
        assert list(gaps(empty, denial_class)) == required
