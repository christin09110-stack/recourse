"""The letter body, assembled from cited assertions.

Pure and deterministic. It composes from structured `Assertion`s; it does not write
prose from nothing, and no language model is anywhere near it. The same inputs always
produce the same letter, which is what makes a draft something a person can check
rather than something they have to re-read every time.

The rule this module enforces: **a clinical assertion must name the document it came
from.** Not as a convention, as a raise. An appeal that asserts a symptom, a
diagnosis or a course of treatment that nothing in the file supports is not weak
advocacy; it is a false statement on an insurance document, made in the patient's
name. `build_letter_body` refuses to write one, and `CitationGuard` refuses to let
the agent try.

Non-clinical sentences need no citation. A claim number, a date, an amount in dispute
and the text of the code being contested are all facts of the record itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.appeal import Assertion, Deadlines
from recourse.domain.models import Claim, ClaimLine, Denial, Plan


class UncitedAssertion(ValueError):
    """A clinical claim with no document behind it."""


@dataclass(frozen=True)
class LetterBody:
    text: str
    #: (sentence, document_id) for every clinical claim, so the console can show the
    #: reader exactly what each one rests on.
    citations: tuple[tuple[str, str], ...]
    attachments: tuple[str, ...]


def _check(assertions: tuple[Assertion, ...]) -> None:
    uncited = [a.text for a in assertions if a.clinical and not a.document_id]
    if uncited:
        raise UncitedAssertion(
            "these clinical statements name no document in the case file, and an "
            "appeal may not assert what the record does not support: "
            + "; ".join(repr(t) for t in uncited)
        )


def _heading(claim: Claim, line: ClaimLine, plan: Plan, denial: Denial) -> list[str]:
    return [
        f"Re: appeal of denied claim {claim.claim_id}",
        f"Member ID: {plan.member_id}    Plan: {plan.name}",
        f"Service: {line.description} on {line.service_date:%d %B %Y}, {line.provider}",
        f"Amount in dispute: {line.patient_responsibility}",
        f"Denial code: CARC {denial.matched_code} — {denial.reason_text}",
    ]


def build_letter_body(
    *,
    claim: Claim,
    line: ClaimLine,
    denial: Denial,
    plan: Plan,
    deadlines: Deadlines,
    assertions: tuple[Assertion, ...],
    attachments: tuple[str, ...] = (),
) -> LetterBody:
    """Compose the appeal. Raises `UncitedAssertion` rather than writing an unsupported claim."""
    _check(assertions)

    lines = _heading(claim, line, plan, denial)
    lines += ["", "I am appealing this denial. My reasons are set out below.", ""]
    lines += [f"{n}. {a.text}" for n, a in enumerate(assertions, start=1)]

    if attachments:
        lines += ["", "Attached in support:"]
        lines += [f"  - {name}" for name in attachments]

    if deadlines.theirs:
        # Stating the plan's own deadline back to it is not decoration. It is the
        # single most useful sentence in the letter, because the clock the insurer
        # owes the claimant is the one nobody else in this process is counting.
        lines += [
            "",
            f"Under {deadlines.basis or 'the governing rules'}, a decision on this "
            f"appeal is due by {deadlines.theirs:%d %B %Y}.",
        ]
        if deadlines.citation:
            lines.append(f"({deadlines.citation})")

    citations = tuple(
        (a.text, a.document_id) for a in assertions if a.clinical and a.document_id
    )
    return LetterBody("\n".join(lines), citations, attachments)
