"""The shape of a plan-type rulebook file.

Every numeric limit in this system is a `Figure`, and a `Figure` refuses to exist
without the URL it was read from. That is deliberate: these numbers end up in a
letter arguing with an insurer, and a figure nobody can trace is a figure nobody can
defend. The check lives in `__post_init__` so an uncited number cannot be introduced
later by a data file, a migration or a well-meaning edit.

Clocks are tuples rather than single values because an ERISA plan may require two
mandatory internal appeals (29 CFR 2560.503-1 (c)(2)), which splits a 60-day
post-service answer into 30 days and then 30 more. One entry per level.
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
        """`"180 days"` — how the console and a letter say it."""
        return f"{self.value} {self.unit}"


@dataclass(frozen=True)
class ClockTable:
    """A limit per service type. Every deadline in the regulation forks here.

    Each entry is one figure per mandatory appeal level, so a two-level post-service
    clock reads as `(30 days, 30 days)` rather than a single 60 nobody can split.
    """

    urgent: tuple[Figure, ...]
    pre_service: tuple[Figure, ...]
    post_service: tuple[Figure, ...]

    def for_service(self, service_type: ServiceType) -> tuple[Figure, ...]:
        return {
            ServiceType.URGENT: self.urgent,
            ServiceType.PRE_SERVICE: self.pre_service,
            ServiceType.POST_SERVICE: self.post_service,
        }[service_type]


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
