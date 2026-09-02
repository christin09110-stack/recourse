"""The guard that refuses an appeal sentence the record does not support.

Runs before every tool call, and **before `EscalationPolicy`** in the interventions
list. Its `Deny` short-circuits: an unsupported clinical claim must never reach a
policy that would weigh it on cost, urgency or autonomy level and find nothing wrong
with it. Ordering is the enforcement here, not a preference.

A `Deny` and never a `Confirm`. There is nothing for a human to approve about a
sentence the case file does not support: offering it for approval would invite
someone, mid-triage and unwell, to wave through a false statement on an insurance
document made in a patient's name. The correct answer to "may I assert this?" when
nothing backs it is no, and no is not a question.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from strands import InterventionHandler
from strands.interventions.actions import Deny, Proceed

from recourse.domain.appeal import Assertion
from recourse.domain.case import CaseFile

UNCITED_RULE = "uncited_clinical_assertion"

#: Tools that seal a draft already written, whose assertions live in the case file
#: rather than in the call's own arguments. Checked because drafting and sending are
#: two calls: one that passed the guard and one that would otherwise skip it.
_SEALING_TOOLS = frozenset({"mark_ready_to_send"})

#: A model may send `clinical` as a JSON string. Anything not explicitly falsey is
#: treated as clinical, so a garbled flag over-reports rather than waving a medical
#: claim through unchecked.
_FALSEY = frozenset({"", "false", "no", "0", "none", "null"})


def _clinical(raw: Any) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() not in _FALSEY
    return bool(raw)


def _as_assertion(raw: Any) -> Assertion | None:
    """One assertion, however the caller shaped it. None when it cannot be read."""
    if isinstance(raw, Assertion):
        return raw
    if isinstance(raw, dict):
        return Assertion(
            text=str(raw.get("text", "")),
            clinical=_clinical(raw.get("clinical", False)),
            document_id=raw.get("document_id") or None,
        )
    return None


class CitationGuard(InterventionHandler):
    name = "recourse-citation"

    def __init__(self, case_file: Callable[[], CaseFile]) -> None:
        #: A callable, not a `CaseFile`. Documents arrive mid-run — the agent
        #: requests one and it lands — and a snapshot taken when the guard was built
        #: would go on refusing an assertion whose support turned up a call ago.
        self.case_file = case_file
        self.refusals: list[str] = []

    def before_tool_call(self, event: Any, **kwargs: Any) -> Any:
        args = event.tool_use.get("input", {}) or {}
        for raw in self._assertions(event.tool_use["name"], args):
            assertion = _as_assertion(raw)
            if assertion is None:
                return self._deny(f"an assertion arrived as {raw!r}, which this guard "
                                  "cannot read, and an unread claim is not a checked one")
            if not assertion.clinical:
                continue  # A claim number or a date is a fact of the record itself.
            if not assertion.document_id:
                return self._deny(f"{assertion.text!r} is a clinical statement citing no "
                                  "document at all")
            if assertion.document_id not in self.case_file().documents:
                return self._deny(f"{assertion.text!r} cites {assertion.document_id!r}, "
                                  "which is not a document in this case file")
        return Proceed(reason="every clinical statement cites a document in the file")

    def _assertions(self, tool_name: str, args: dict[str, Any]) -> tuple[Any, ...]:
        """Found by shape first, so a letter-writing tool added later cannot slip past
        by not being on a list."""
        if "assertions" in args:
            return tuple(args.get("assertions") or ())
        if tool_name in _SEALING_TOOLS:
            appeal = self.case_file().appeals.get(args.get("appeal_id"))
            return tuple(appeal.assertions) if appeal else ()
        return ()

    def _deny(self, detail: str) -> Deny:
        self.refusals.append(detail)
        return Deny(reason=f"{UNCITED_RULE}: {detail}")
