"""Reading the rulebook, and refusing to guess.

The one behaviour that matters here is the refusal. `for_plan_type` raises on a plan
type it has no clock table for, and nothing in this codebase catches that and
substitutes a default. Non-health ERISA plans allow a claimant 60 days to appeal,
not 180 (29 CFR 2560.503-1 (h)(2)(i)); handing back the health figure would tell
someone they had four more months than the law gives them, which is the single
direction an error in this file must never take. A loud stop is recoverable. A
generous deadline is not.

`erisa-non-health.json` ships for exactly that reason: it is a real file with a real
citation whose only job is to be turned down with the correct number in the message.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from recourse.domain.types import PlanType
from recourse.rulebook import parse
from recourse.rulebook.schema import PlanRules

DATA_DIR = Path(__file__).parent / "data"


class PlanTypeNotInScope(LookupError):
    """Raised for a plan type Recourse has no clock table for. Never caught."""


def _path_for(name: str) -> Path:
    return DATA_DIR / f"{name.replace('_', '-')}.json"


@lru_cache(maxsize=None)
def _raw(name: str) -> dict[str, Any] | None:
    path = _path_for(name)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def for_plan_type(plan_type: PlanType | str) -> PlanRules:
    """The rules for one plan type, or a refusal naming the number we would get wrong."""
    name = plan_type.value if isinstance(plan_type, PlanType) else str(plan_type)
    raw = _raw(name)
    if raw is None:
        raise PlanTypeNotInScope(
            f"no rulebook for plan type {name!r}: Recourse ships clock tables for "
            f"{', '.join(t.value for t in available_plan_types())} only, and it will "
            f"not compute a deadline from a table it does not have.",
        )
    if not raw.get("in_scope", False):
        raise PlanTypeNotInScope(_refusal(name, raw))
    return parse.plan_rules(raw)


def _refusal(name: str, raw: dict[str, Any]) -> str:
    """Say what was asked for, and the figure that would have been wrong."""
    appeal = raw.get("time_to_appeal", {})
    figure = f"{appeal.get('value')} {appeal.get('unit')}".strip()
    reason = raw.get("out_of_scope_reason", "this plan type is out of scope")
    citation = appeal.get("citation", raw.get("source", ""))
    return (
        f"plan type {name!r} is out of scope and will not be defaulted: {reason} "
        f"A claimant on this plan has {figure} to appeal ({citation}), not the "
        f"180 days a health plan allows, and applying the health figure would tell "
        f"them they had four months they do not have."
    )


@lru_cache(maxsize=None)
def available_plan_types() -> tuple[PlanType, ...]:
    """Only the plan types with a full clock table. Order follows `PlanType`."""
    found = []
    for plan_type in PlanType:
        raw = _raw(plan_type.value)
        if raw is not None and raw.get("in_scope", False):
            found.append(plan_type)
    return tuple(found)


def shipped_files() -> tuple[Path, ...]:
    """Every plan-type file on disk, in-scope or not, for the citation audit.

    Filtered on `plan_type` so that the code table, which lands in this directory
    later and has a different shape, does not get walked as though it were a plan.
    """
    plans = [p for p in sorted(DATA_DIR.glob("*.json")) if "plan_type" in _raw(p.stem)]
    return tuple(plans)
