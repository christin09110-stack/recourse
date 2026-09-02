"""JSON to `PlanRules`.

Kept apart from `loader.py` so that the refusal logic — the part that must never
quietly hand back a default — reads on one screen without parsing noise around it.

Nothing here supplies a fallback. A missing key raises, because a rulebook file that
half-loaded would produce a deadline that is confidently wrong.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.types import AppealStage, PlanType
from recourse.rulebook.schema import (
    ClockTable,
    DecisionClocks,
    ExternalReview,
    Figure,
    NextStep,
    PlanRules,
)


def figure(raw: dict[str, Any]) -> Figure:
    extension = raw.get("extension")
    return Figure(
        value=int(raw["value"]),
        unit=str(raw["unit"]),
        citation=str(raw["citation"]),
        note=str(raw.get("note", "")),
        extension=figure(extension) if extension else None,
    )


def clock_table(raw: dict[str, Any]) -> ClockTable:
    return ClockTable(
        urgent=tuple(figure(f) for f in raw["urgent"]),
        pre_service=tuple(figure(f) for f in raw["pre_service"]),
        post_service=tuple(figure(f) for f in raw["post_service"]),
    )


def external_review(raw: dict[str, Any] | None) -> ExternalReview | None:
    """`None` where the source we cite does not state the external-review clocks.

    Absent is not zero and not "same as ACA". A caller that needs the figure gets
    nothing and must say so, rather than being handed a borrowed one.
    """
    if not raw:
        return None
    return ExternalReview(
        request_within=figure(raw["request_within"]),
        standard_decision=figure(raw["standard_decision"]),
        expedited_decision=figure(raw["expedited_decision"]),
    )


def next_step(raw: dict[str, Any]) -> NextStep:
    return NextStep(
        stage=AppealStage(raw["stage"]),
        condition=str(raw["condition"]),
        citation=str(raw["citation"]),
        note=str(raw.get("note", "")),
    )


def plan_rules(raw: dict[str, Any]) -> PlanRules:
    return PlanRules(
        plan_type=PlanType(raw["plan_type"]),
        label=str(raw["label"]),
        internal_levels=int(raw["internal_levels"]),
        time_to_appeal=figure(raw["time_to_appeal"]),
        initial_notice=clock_table(raw["initial_notice"]),
        decision_on_appeal=DecisionClocks(
            tables=tuple(clock_table(t) for t in raw["decision_on_appeal"]),
        ),
        after_exhaustion=tuple(next_step(s) for s in raw["after_exhaustion"]),
        source=str(raw["source"]),
        external_review=external_review(raw.get("external_review")),
    )
