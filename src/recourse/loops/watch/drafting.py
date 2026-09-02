"""Turning what the model sent into an appeal the case file will accept.

Two jobs, both about not letting the model's shape become the record's shape.

`as_assertions` reads assertions however they arrived — JSON from the model, or
`Assertion`s from a caller — and refuses anything it cannot read rather than
coercing it. An unreadable claim is not a checked one, and `str(raw)` on a garbled
object would put whatever it happened to render as into a letter.

`appeal_for` finds the open appeal a draft belongs to, or opens one. The id and the
start date are both derived here from the denial and the notice date, never taken
from the model: an appeal opened on a date the model supplied is a countdown started
from a number nobody checked.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.appeal import Appeal, Assertion
from recourse.loops.lookup import Resolved
from recourse.persistence.store import CaseStore

#: A model may send `clinical` as a JSON string. Anything not explicitly falsey counts
#: as clinical, so a garbled flag over-reports rather than waving a medical claim
#: through unchecked. Same table as `policy.citation`, and for the same reason.
_FALSEY = frozenset({"", "false", "no", "0", "none", "null"})


def _clinical(raw: Any) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() not in _FALSEY
    return bool(raw)


def as_assertions(raw: Any) -> tuple[tuple[Assertion, ...], str | None]:
    """Every assertion, or a refusal naming the one that could not be read."""
    built: list[Assertion] = []
    for item in raw or ():
        if isinstance(item, Assertion):
            built.append(item)
        elif isinstance(item, dict):
            built.append(Assertion(
                text=str(item.get("text", "")),
                clinical=_clinical(item.get("clinical", False)),
                document_id=item.get("document_id") or None,
            ))
        else:
            return (), (f"an assertion arrived as {item!r}, which cannot be read as a "
                        "sentence and a document; send {text, clinical, document_id}")
    return tuple(built), None


def appeal_for(store: CaseStore, resolved: Resolved) -> Appeal:
    """The open appeal this draft belongs to, opened if there is not one yet.

    `started_on` is the claim's own notice date, which is what the 180 days run from.
    Nothing about it comes from the model.
    """
    if resolved.appeal is not None:
        return resolved.appeal
    return store.open_appeal(Appeal.opened(
        appeal_id=f"appeal-{resolved.denial.denial_id.removeprefix('den-')}",
        denial_id=resolved.denial.denial_id,
        plan_id=resolved.plan.plan_id,
        started_on=resolved.claim.notice_date,
    ))
