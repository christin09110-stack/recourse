"""The WATCH agent's tool set: five tools, and there is no sixth.

Three read (`reading.py`) and two change something (`writing.py`). Nothing here
files an appeal, marks one filed, or sends anything to an insurer. Filing is a legal
act taken in the patient's name, and that rule is enforced by the absence of the
capability rather than by a guard some autonomy level could reach past. A test
asserts this exact list, so a filing tool added later fails the suite rather than
being discovered in a demo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from recourse.loops.watch.reading import build_reading_tools
from recourse.loops.watch.writing import build_writing_tools
from recourse.persistence.store import CaseStore

#: The whole set, by name. `EscalationPolicy.GUARDED_TOOLS` covers the two that
#: change something; the other three commit nothing and reach nobody.
WATCH_TOOLS: tuple[str, ...] = (
    "list_denials", "explain_denial", "check_evidence",
    "draft_letter_body", "request_document",
)


def build_watch_tools(
    store: CaseStore,
    clock: Callable[[], date],
    requests: list[dict[str, Any]] | None = None,
) -> list[Any]:
    """The five tools, closed over one case file and one clock."""
    return [
        *build_reading_tools(store, clock),
        *build_writing_tools(store, clock, [] if requests is None else requests),
    ]
