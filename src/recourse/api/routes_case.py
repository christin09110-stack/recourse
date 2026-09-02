"""The world and the case file: what is on the record, before anyone acts on it.

`GET /api/world` sends the frozen clock, and the console stamps every timestamp from
it rather than from `new Date()`. The demo runs on a fixed date so a recorded
countdown is reproducible; a browser that used its own clock would show one set of
figures in the recording and a different set on playback.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from recourse.api.denial_view import denial_view
from recourse.api.serialise import claim_view, document_view, plan_view
from recourse.api.state import RecourseState
from recourse.domain.models import Plan
from recourse.rulebook.loader import PlanTypeNotInScope, for_plan_type


def _rules_view(plan: Plan) -> dict[str, Any]:
    """The clock table behind one plan, or the refusal that replaces it.

    A plan type with no table is reported as a refusal with its reason, not omitted
    and not defaulted. Non-health ERISA plans allow 60 days rather than 180, and a
    console that quietly showed nothing there would be the polite version of showing
    the wrong number.
    """
    try:
        rules = for_plan_type(plan.plan_type)
    except PlanTypeNotInScope as exc:
        return {"in_scope": False, "refusal": str(exc)}
    return {
        "in_scope": True,
        "label": rules.label,
        "time_to_appeal": rules.time_to_appeal.label,
        "time_to_appeal_citation": rules.time_to_appeal.citation,
        "internal_levels": rules.internal_levels,
        "external_review": rules.external_review is not None,
        "source": rules.source,
    }


def add_case_routes(app: FastAPI) -> None:
    @app.get("/api/world")
    def get_world() -> dict[str, Any]:
        """The frozen clock, the plans and the dial. The console's first call."""
        state: RecourseState = app.state.recourse
        case = state.case
        return {
            "now": state.world.now().isoformat(),
            "now_at": state.world.now_at().isoformat(),
            "case_id": case.case_id,
            "autonomy": state.autonomy.value,
            "plans": [
                {**plan_view(plan), "rules": _rules_view(plan)}
                for plan in case.plans.values()
            ],
        }

    @app.get("/api/case")
    def get_case() -> dict[str, Any]:
        """The whole file: claims, their lines, the documents and the denials."""
        state: RecourseState = app.state.recourse
        case = state.case
        return {
            "case_id": case.case_id,
            "claims": [claim_view(claim) for claim in case.claims.values()],
            "documents": [document_view(doc) for doc in case.documents.values()],
            # The denials in full, not their ids. The Case file screen shows which
            # lines were refused and why, and a screen that had to fetch a second
            # route to find that out would render the episode once without it.
            "denials": [denial_view(case, denial) for denial in case.denials.values()],
        }

    @app.get("/api/denials")
    def get_denials() -> list[dict[str, Any]]:
        """Every denial with its class, its matched code and its evidence gaps."""
        state: RecourseState = app.state.recourse
        case = state.case
        return [denial_view(case, denial) for denial in case.denials.values()]
