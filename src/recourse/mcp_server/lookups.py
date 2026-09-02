"""The lookups behind the read-only MCP tools: codes, plan rules, evidence.

Plain functions returning plain dicts, so the tool definitions in `server.py` stay
readable as a list of what is exposed rather than as a wall of serialisation. Every
figure that leaves here carries the URL it was read from: a number quoted at an
insurer without provenance is a number the claimant cannot defend.
"""

from __future__ import annotations

from typing import Any

from recourse.domain import evidence
from recourse.domain.codes import classify
from recourse.domain.types import DenialClass, PlanType
from recourse.rulebook.loader import for_plan_type


def classification(carc: list[str], rarc: list[str]) -> dict[str, Any]:
    """One line's codes, as a class and the row that produced it."""
    found = classify(tuple(carc), tuple(rarc))
    return {
        "denial_class": found.denial_class.value,
        "assessable": found.is_assessable,
        "reason": found.reason,
        "matched": _row(found.matched),
        "narrowed_by": _row(found.detail),
        # The codes this build does not know. Returned rather than dropped: an
        # unrecognised code is the fact the caller most needs, and it is why the
        # class came back unassessable instead of being guessed at.
        "unknown_codes": list(found.unknown_codes),
    }


def _row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "code": row.code, "system": row.system, "text": row.text,
        "denial_class": row.denial_class.value, "generic": row.generic,
        "citation": row.citation,
    }


def _figure(figure: Any) -> dict[str, Any]:
    return {"value": figure.value, "unit": figure.unit, "label": figure.label,
            "citation": figure.citation, "note": figure.note}


def _table(table: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        service: [_figure(f) for f in getattr(table, service)]
        for service in ("urgent", "pre_service", "post_service")
    }


def plan_rules(plan_type: str) -> dict[str, Any]:
    """Every clock a plan type carries, with its citation. Raises if out of scope."""
    rules = for_plan_type(PlanType(plan_type))
    review = rules.external_review
    return {
        "plan_type": rules.plan_type.value,
        "label": rules.label,
        "internal_levels": rules.internal_levels,
        "time_to_appeal": _figure(rules.time_to_appeal),
        "initial_notice": _table(rules.initial_notice),
        "decision_on_appeal": [
            _table(t) for t in rules.decision_on_appeal.tables
        ],
        "external_review": {
            "request_within": _figure(review.request_within),
            "standard_decision": _figure(review.standard_decision),
            "expedited_decision": _figure(review.expedited_decision),
        } if review else None,
        "after_exhaustion": [
            {"stage": step.stage.value, "condition": step.condition,
             "citation": step.citation, "note": step.note}
            for step in rules.after_exhaustion
        ],
        "source": rules.source,
    }


def requirements(denial_class: str) -> list[dict[str, Any]]:
    """The documents an appeal of this class needs, and what each establishes."""
    return [
        {"kind": r.kind, "why": r.why, "required": r.required}
        for r in evidence.requirements_for(DenialClass(denial_class))
    ]
