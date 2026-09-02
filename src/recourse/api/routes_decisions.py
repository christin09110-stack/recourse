"""The queue of questions, and what answering one actually does.

**A decline ends the run here, in our own code, and is never handed back to the
agent.** Muster resumed on any answer and trusted the SDK's `evaluate` callback to
refuse the paused tool call. Against the deployed service that refusal did not hold:
an operator declined a change, the resumed run performed it anyway, and the receipt
carried the name of the person who had refused it. A decline that does the declined
thing and then attributes it to the refuser is the worst failure a product like this
can have, and it is not something to delegate to a framework callback.

So the outcome is recorded, the journal says a person refused, and nothing else
happens. The denial keeps its state and the clock keeps running, which is honest:
declining to draft is not the same as the problem going away, and the deadline
sweep will raise it again.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from recourse.api.decisions_view import pending_view
from recourse.api.parking import open_decision
from recourse.api.state import RecourseState
from recourse.domain.types import DecisionOutcome


class DecisionAnswerIn(BaseModel):
    outcome: DecisionOutcome
    by: str
    #: How this person relates to the patient — "self", "daughter", "care manager".
    #: It goes on the record beside their name, because who decided matters as much
    #: as what they decided when the record is somebody's defence.
    role: str
    note: str = ""


def add_decision_routes(app: FastAPI, decision_resumer: Any) -> None:
    @app.get("/api/decisions")
    def get_decisions() -> list[dict[str, Any]]:
        """Every question still waiting for a person."""
        state: RecourseState = app.state.recourse
        return [pending_view(p, state.case) for p in state.inbox.pending()]

    @app.post("/api/decisions/{decision_id}/answer")
    async def answer_decision(decision_id: str, payload: DecisionAnswerIn) -> dict[str, Any]:
        state: RecourseState = app.state.recourse
        if state.inbox.get(decision_id) is None:
            raise HTTPException(status_code=404, detail=f"no pending decision {decision_id!r}")

        pending = state.inbox.answer(
            decision_id, payload.outcome, by=payload.by, role=payload.role, note=payload.note,
        )
        appeal_id = pending.decision.appeal_id or None
        state.journal.write(
            kind="decision_answered",
            sentence=f"{payload.by} ({payload.role}) {payload.outcome.value}d: "
                     f"{pending.decision.prompt}",
            at=state.world.now_at(), appeal_id=appeal_id, decided_by=payload.by,
        )

        # See the module docstring. The resumer is not called at all on a decline.
        if pending.decision.outcome is DecisionOutcome.DECLINE:
            return {
                "status": "declined",
                "decision_id": decision_id,
                "appeal_id": appeal_id,
                "changed": False,
                "detail": "Nothing was done. The appeal is exactly as it was, and its "
                          "deadline is still running.",
            }

        result = await decision_resumer(state, pending)
        if getattr(result, "paused", False):
            return {"status": "awaiting_decision", "decision_id": open_decision(state, result)}
        return {"status": "done", "changed": True, "text": getattr(result, "text", "")}
