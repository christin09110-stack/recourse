"""The shape of a plan-type rulebook file.

A `Figure` refuses to exist without the URL it was read from: these numbers end up in
a letter arguing with an insurer, and the check sits in `__post_init__` so that no
later data file can slip an uncited one in. Clocks are tuples because an ERISA plan
may require two mandatory internal appeals (29 CFR 2560.503-1 (c)(2)), which splits a
60-day post-service answer into 30 days and then 30 more: one entry per level.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.types import AppealStage, PlanType, ServiceType

UNITS = ("hours", "days", "months")


@dataclass(frozen=True)
class Figure:
    """One regulated limit, and where it was read from."""

    value: int
    unit: str
    citation: str
    note: str = ""
    #: Some ERISA initial-notice periods may be extended once, by a further period.
    extension: Figure | None = None

    def __post_init__(self) -> None:
        if not self.citation.strip():
            raise ValueError(f"figure '{self.value} {self.unit}' carries no citation")
        if self.unit not in UNITS:
            raise ValueError(f"unit {self.unit!r} is not one of {UNITS}")

    @property
    def label(self) -> str:
        return f"{self.value} {self.unit}"  # "180 days", as a letter would say it


@dataclass(frozen=True)
class ClockTable:
    """A limit per service type, one figure per mandatory appeal level."""

    urgent: tuple[Figure, ...]
    pre_service: tuple[Figure, ...]
    post_service: tuple[Figure, ...]

    def for_service(self, service_type: ServiceType) -> tuple[Figure, ...]:
        # The fields are named for the ServiceType values so that adding a service
        # type without adding its clock fails here rather than returning a wrong one.
        return getattr(self, service_type.value)


@dataclass(frozen=True)
class DecisionClocks:
    """How long the plan has to answer, indexed by how many levels it requires."""

    tables: tuple[ClockTable, ...]

    def for_levels(self, levels: int) -> ClockTable:
        if not 1 <= levels <= len(self.tables):
            raise ValueError(
                f"this plan type ships clocks for 1..{len(self.tables)} internal "
                f"levels; {levels} was asked for",
            )
        return self.tables[levels - 1]


@dataclass(frozen=True)
class ExternalReview:
    request_within: Figure
    standard_decision: Figure
    expedited_decision: Figure


@dataclass(frozen=True)
class NextStep:
    """What follows a final internal denial, and when it applies."""

    stage: AppealStage
    condition: str  # "always" | "non_grandfathered" | "grandfathered"
    citation: str
    note: str = ""


@dataclass(frozen=True)
class PlanRules:
    plan_type: PlanType
    label: str
    internal_levels: int
    time_to_appeal: Figure
    initial_notice: ClockTable
    decision_on_appeal: DecisionClocks
    after_exhaustion: tuple[NextStep, ...]
    source: str
    external_review: ExternalReview | None = None
