"""What a credible appeal of each kind needs, and what the file is missing.

This is the module that lets the agent say "I can prepare this one" rather than
guessing. The lists are deliberately short: every extra document asked of a patient
is another organisation to chase while ill. A requirement is `required` when the
appeal is not credible without it and merely strengthens it otherwise; only required
ones produce a gap.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.case import CaseFile
from recourse.domain.types import DenialClass


@dataclass(frozen=True)
class Requirement:
    """One document an appeal of some class wants, and what it establishes."""

    kind: str          # matches Document.kind
    why: str
    required: bool = True


def _r(kind: str, why: str, *, required: bool = True) -> Requirement:
    return Requirement(kind=kind, why=why, required=required)


_REQUIREMENTS: dict[DenialClass, tuple[Requirement, ...]] = {
    DenialClass.CLERICAL: (
        _r("eob", "Shows the denied line, the amount at stake and the code being contested."),
        # The corrected claim detail comes from the provider's biller, not the
        # patient. Marking it required would park a fixable denial behind a
        # document the person cannot produce, which is how these appeals die.
        _r("corrected_claim", "The provider's corrected billing detail, if any.", required=False),
    ),
    DenialClass.AUTHORIZATION: (
        _r("authorization", "The approval, or proof the request was made. The approval often "
                            "exists already and was simply never attached to the claim."),
        _r("denial_letter", "Fixes the date and wording of the refusal being answered.",
           required=False),
    ),
    DenialClass.ELIGIBILITY: (
        _r("coverage_record", "Establishes that coverage was in force on the date of service."),
    ),
    DenialClass.COVERAGE: (
        _r("coverage_record", "The plan document language the exclusion is being read from, "
                              "which is what the appeal argues against."),
        _r("denial_letter", "Names the clause the insurer relied on.", required=False),
    ),
    DenialClass.TIMELINESS: (
        _r("proof_of_timely_filing", "Shows when the claim was submitted. A late filing is "
                                     "usually the provider's lapse, and the patient may not be "
                                     "liable for it at all."),
    ),
    DenialClass.CLINICAL: (
        # Nothing substitutes for this one. A medical-necessity denial is answered by
        # the treating clinician's judgement or it is not answered.
        _r("clinical_note", "A letter of medical necessity from the treating clinician. "
                            "Nothing else can make this argument."),
    ),
    # UNASSESSABLE is absent on purpose: see requirements_for.
}

#: Classes the agent may never call preparable, whatever the file holds.
_NEVER_ALONE = (DenialClass.CLINICAL, DenialClass.UNASSESSABLE)


def requirements_for(denial_class: DenialClass) -> tuple[Requirement, ...]:
    """The documents an appeal of this class needs.

    UNASSESSABLE returns empty: the insurer gave no reason we recognise, and inventing
    a requirement list for it would dress a guess up as a checklist. The caller
    escalates instead.
    """
    return _REQUIREMENTS.get(denial_class, ())


def gaps(case_file: CaseFile, denial_class: DenialClass) -> tuple[Requirement, ...]:
    """The required documents this case file cannot supply."""
    return tuple(
        req for req in requirements_for(denial_class)
        if req.required and not case_file.documents_of_kind(req.kind)
    )


def can_prepare_alone(case_file: CaseFile, denial_class: DenialClass) -> bool:
    """Whether the agent may draft this appeal without a person.

    A CLINICAL denial is never preparable alone even with the letter of medical
    necessity already on file. The gap there is not a missing document, it is
    authorship: the argument is the treating clinician's to make, and the agent's job
    is to assemble what the clinician said, not to author a medical judgement in their
    name. UNASSESSABLE is excluded for the mirror reason — with no recognised denial
    reason there is nothing to prepare against, and unknown is never benign.
    """
    return denial_class not in _NEVER_ALONE and not gaps(case_file, denial_class)
