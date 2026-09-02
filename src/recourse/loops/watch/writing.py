"""The two WATCH tools that change something: the draft, and the ask for a document.

Neither files anything. `draft_letter_body` leaves `sent_on` unset and there is no
tool anywhere in this system that sets it; `request_document` asks a third party for
paperwork in the claimant's name, which is why the autonomy dial has an opinion about
it and why it is in `GUARDED_TOOLS`.

`{"error": ...}` is the refusal shape. `build_letter_body` raises `UncitedAssertion`
on a clinical sentence with nothing behind it, and it arrives here as a refusal the
model can act on rather than as a traceback that would end the run with no record of
what it tried to write.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from strands import tool

from recourse.domain.evidence import gaps, requirements_for
from recourse.domain.packet import UncitedAssertion, build_letter_body
from recourse.loops.lookup import deadlines_at_notice, resolve_denial
from recourse.loops.watch.drafting import appeal_for, as_assertions
from recourse.persistence.store import CaseStore


def build_writing_tools(
    store: CaseStore, clock: Callable[[], date], requests: list[dict[str, Any]],
) -> list[Any]:
    """`requests` is the caller's list, so the journal reads the asks the agent made."""

    @tool
    def draft_letter_body(
        denial_id: str,
        assertions: list[dict[str, Any]],
        attachments: list[str] | None = None,
    ) -> Any:
        """Compose the appeal letter body from cited assertions and attach it.

        Drafting is not sending: the letter lands on the appeal with `sent_on` unset.
        """
        resolved, error = resolve_denial(store.case, denial_id)
        if error:
            return {"error": error}
        missing = gaps(store.case, resolved.denial.denial_class)
        if missing:
            # Refused, not drafted around. A medical-necessity appeal with no letter
            # from the treating clinician is not a weaker appeal; it is an argument
            # nobody qualified has made, written in the patient's name.
            return {"error": f"this {resolved.denial.denial_class.value} denial cannot be "
                             "drafted from what the case file holds. Missing: "
                             + "; ".join(f"{r.kind} ({r.why})" for r in missing)}
        said, unreadable = as_assertions(assertions)
        if unreadable:
            return {"error": unreadable}
        clocks = deadlines_at_notice(resolved)
        if clocks is None:
            return {"error": "no clock table ships for plan type "
                             f"{resolved.plan.plan_type.value!r}"}
        appeal = appeal_for(store, resolved)
        try:
            letter = build_letter_body(
                claim=resolved.claim, line=resolved.line, denial=resolved.denial,
                plan=resolved.plan, deadlines=clocks, assertions=said,
                attachments=tuple(attachments or ()),
            )
        except UncitedAssertion as exc:
            return {"error": str(exc)}
        store.attach_letter(appeal.appeal_id, letter.text, said)
        return {"appeal_id": appeal.appeal_id, "denial_id": denial_id, "sent": False,
                "body": letter.text, "citations": [list(c) for c in letter.citations]}

    @tool
    def request_document(denial_id: str, kind: str, from_whom: str) -> Any:
        """Ask a provider or the plan for a document this appeal is missing."""
        resolved, error = resolve_denial(store.case, denial_id)
        if error:
            return {"error": error}
        wanted = {r.kind for r in requirements_for(resolved.denial.denial_class)}
        if kind not in wanted:
            # Name what would be accepted. A refusal that only rejects sends the model
            # guessing, and four guesses later the document is still not asked for.
            return {"error": f"an appeal of this class does not need {kind!r}; it needs "
                             f"one of {', '.join(sorted(wanted)) or 'nothing on file'}"}
        ask = {"denial_id": denial_id, "kind": kind, "from_whom": from_whom,
               "asked_on": clock().isoformat()}
        requests.append(ask)
        return {"requested": True, **ask}

    return [draft_letter_body, request_document]
