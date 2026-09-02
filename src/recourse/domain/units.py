"""Turning a regulation's figure into whole days, and ordering the stages.

The regulations state their limits in three different units — 72 hours, 15 days,
four months — and every one of them has to become a date on a calendar. That
conversion is small and easy to get subtly wrong, so it lives on its own with its
rounding rule written down.
"""

from __future__ import annotations

from recourse.domain.types import AppealStage
from recourse.rulebook.schema import Figure

#: Roughly a month. Only ever applied to the external-review window, which the
#: regulations state in months rather than days.
DAYS_PER_MONTH = 30


def days(figure: Figure) -> int:
    """A figure in whatever unit the regulation used, as whole days."""
    if figure.unit == "days":
        return int(figure.value)
    if figure.unit == "months":
        return int(figure.value) * DAYS_PER_MONTH
    if figure.unit == "hours":
        # Ceiling: a 72-hour clock that expires mid-day expires that day, and
        # rounding down would hand back a day the claimant does not have.
        return -(-int(figure.value) // 24)
    raise ValueError(f"unknown unit {figure.unit!r} on a clock figure")


def internal_stage_index(stage: AppealStage) -> int:
    """0 for the first mandatory internal appeal, 1 for the second."""
    return {AppealStage.INTERNAL_1: 0, AppealStage.INTERNAL_2: 1}[stage]
