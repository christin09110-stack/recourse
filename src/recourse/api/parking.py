"""Parking a paused run, so a person can answer it later.

One place, because both loops and the resume path park runs the same way and a
second copy is a second chance to drop the snapshot, the interrupt id or the
proposal — and a decision parked without its snapshot can never be resumed at all.

The appeal id is derived from the stopped call's own arguments rather than passed in
by the caller. The question a person is answering has to name the claim it is about,
and the only thing that reliably knows which claim that is, is the call that stopped.
"""

from __future__ import annotations

import uuid
from typing import Any

from recourse.api.state import RecourseState
from recourse.persistence.decisions import Decision


def appeal_id_for(state: RecourseState, proposal: dict[str, Any]) -> str:
    """The appeal the stopped call was about, read from its arguments."""
    appeal_id = str(proposal.get("appeal_id") or "")
    if appeal_id:
        return appeal_id
    denial_id = str(proposal.get("denial_id") or "")
    if not denial_id:
        return ""
    found = next(
        (a for a in state.case.appeals.values() if a.denial_id == denial_id), None,
    )
    return found.appeal_id if found else ""


def open_decision(state: RecourseState, result: Any) -> str:
    """Park a paused run in the inbox and return the new decision id."""
    proposal = getattr(result, "proposal", {}) or {}
    appeal_id = appeal_id_for(state, proposal)
    decision_id = f"dec-{uuid.uuid4().hex[:8]}"
    decision = Decision(
        decision_id=decision_id,
        rule=result.interrupt_reason or "unknown",
        prompt=result.text,
        appeal_id=appeal_id,
    )
    state.inbox.open(
        decision,
        # An empty interrupt id would park a decision that can never be resumed.
        # It is kept as it arrived rather than defaulted, so the failure is visible
        # in the record instead of at resume time, hours after somebody answered.
        interrupt_id=result.interrupt_id or "",
        snapshot=result.snapshot or {},
        rule_hits=list(result.rule_hits or []),
        proposal=proposal,
    )
    state.journal.write(
        kind="escalated",
        sentence=f"Recourse stopped and asked: {decision.prompt}",
        at=state.world.now_at(),
        appeal_id=appeal_id or None,
    )
    return decision_id
