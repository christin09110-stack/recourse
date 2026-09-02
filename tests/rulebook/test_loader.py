"""The rulebook, and the refusal it exists to make."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from recourse.domain.types import PlanType, ServiceType
from recourse.rulebook import loader
from recourse.rulebook.schema import Figure


def _figures(node: Any, trail: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Every object anywhere in the file that looks like a regulated number."""
    if isinstance(node, dict):
        here = [(trail, node)] if {"value", "unit"} <= node.keys() else []
        return here + [f for k, v in node.items() for f in _figures(v, f"{trail}.{k}")]
    if isinstance(node, list):
        return [f for i, c in enumerate(node) for f in _figures(c, f"{trail}[{i}]")]
    return []


@pytest.mark.parametrize("path", loader.shipped_files(), ids=lambda p: p.name)
def test_every_figure_carries_a_citation(path) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    figures = _figures(raw, path.stem)
    assert figures, f"{path.name} ships no figures at all"
    for trail, figure in figures:
        assert figure.get("citation", "").strip(), f"{trail} has no citation"
        assert figure["citation"].startswith("https://"), f"{trail} cites {figure['citation']!r}"


def test_aca_gives_180_days_to_appeal() -> None:
    rules = loader.for_plan_type(PlanType.ACA_MARKETPLACE)
    assert rules.time_to_appeal.value == 180
    assert rules.time_to_appeal.unit == "days"
    assert "healthcare.gov" in rules.time_to_appeal.citation


def test_aca_post_service_decision_is_60_days() -> None:
    rules = loader.for_plan_type(PlanType.ACA_MARKETPLACE)
    table = rules.decision_on_appeal.for_levels(1)
    (decision,) = table.for_service(ServiceType.POST_SERVICE)
    assert decision.value == 60


def test_erisa_two_levels_split_post_service_into_30_plus_30() -> None:
    rules = loader.for_plan_type(PlanType.ERISA_GROUP_HEALTH)
    one_level = rules.decision_on_appeal.for_levels(1)
    assert [f.value for f in one_level.for_service(ServiceType.POST_SERVICE)] == [60]

    two_levels = rules.decision_on_appeal.for_levels(2)
    assert [f.value for f in two_levels.for_service(ServiceType.POST_SERVICE)] == [30, 30]
    assert [f.value for f in two_levels.for_service(ServiceType.PRE_SERVICE)] == [15, 15]


def test_erisa_ships_no_third_level() -> None:
    rules = loader.for_plan_type(PlanType.ERISA_GROUP_HEALTH)
    with pytest.raises(ValueError):
        rules.decision_on_appeal.for_levels(3)


def test_non_health_erisa_is_refused_and_the_message_says_60_days() -> None:
    """The whole point. A default here would gift someone four months they lack."""
    with pytest.raises(loader.PlanTypeNotInScope) as excinfo:
        loader.for_plan_type(PlanType.ERISA_NON_HEALTH)
    message = str(excinfo.value)
    assert "erisa_non_health" in message
    assert "60 days" in message
    assert "180" in message


def test_unknown_plan_type_is_refused() -> None:
    with pytest.raises(loader.PlanTypeNotInScope) as excinfo:
        loader.for_plan_type("medicare_advantage")
    assert "medicare_advantage" in str(excinfo.value)


def test_available_plan_types_excludes_the_out_of_scope_one() -> None:
    assert loader.available_plan_types() == (
        PlanType.ACA_MARKETPLACE,
        PlanType.ERISA_GROUP_HEALTH,
    )


def test_loaded_rules_cannot_be_mutated() -> None:
    rules = loader.for_plan_type(PlanType.ACA_MARKETPLACE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rules.time_to_appeal = Figure(1, "days", "https://example.test")
    with pytest.raises(dataclasses.FrozenInstanceError):
        rules.time_to_appeal.value = 365


def test_a_figure_without_a_citation_will_not_construct() -> None:
    with pytest.raises(ValueError, match="citation"):
        Figure(value=180, unit="days", citation="  ")
