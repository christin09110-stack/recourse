"""The negative result, and the fix it earned.

Recorded first as an observed defect, and kept as the regression test for it.

Recourse refuses a plan type it has no clock table for, loudly, and that refusal is
the right call. What was not expected is where the refusal lands.

Put one appeal on an out-of-scope plan into a case file — a disability claim filed
alongside the health ones, which is an ordinary thing for a household to have — and
`policy.sweep.sweep` raises `PlanTypeNotInScope` on reaching it. Sweep is not a
detail: it is `GET /api/deadlines`, it is the PRESS loop's `sweep_deadlines`, and it
is the screen the product is built around. So one unreadable plan takes down every
clock in the file, including the appeal at day 150 of 180 that the whole design
exists to shout about. The failure mode rule 3 was written to prevent — silence as
the window closes — arrives through the door marked "we refuse to guess".

The gap is narrow and it is real: two other paths ask the same question and both
handle it. `api.clocks_view.deadlines_of` and `loops.lookup.deadlines_of` each catch
`PlanTypeNotInScope` and return None, which is why `GET /api/appeals` degrades to
"unassessable" while `GET /api/deadlines` returns 500. `sweep` calls
`clocks.deadlines_for` directly and catches nothing, and its own comment says the
caller escalates such an appeal as unassessable. No caller does.

**This was found by writing the eval suite, and then fixed.** `sweep` now catches
the refusal per appeal, emits a finding that says so in plain words, and carries on
with the rest of the file. Refusing to compute one clock must never stop us
reporting the others, and the one we could not read is itself worth raising.

The assertions below are the fix, stated as the behaviour a person depends on.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from recourse.api.app import create_app
from recourse.domain.types import PlanType
from recourse.policy.sweep import sweep
from tests.evals.support import seeded


@pytest.fixture
def world():
    return seeded()[0]


@pytest.fixture
def case(world):
    return world.case_file()


def _with_a_disability_appeal(case):
    """Add one appeal on a plan type this build has no clock table for."""
    case.plans["plan-ltd"] = replace(
        case.plans["plan-erisa"], plan_id="plan-ltd",
        plan_type=PlanType.ERISA_NON_HEALTH, internal_levels=1,
    )
    case.appeals["appeal-ltd"] = replace(
        case.appeals["appeal-197"], appeal_id="appeal-ltd", plan_id="plan-ltd",
    )
    return case


def test_one_unreadable_plan_does_not_silence_the_rest_of_the_file(case, world):
    """A household with a disability claim alongside its health ones is ordinary.
    That one appeal used to take every clock down with it — including the one at
    day 150 of 180 that the whole design exists to shout about."""
    dirtied = _with_a_disability_appeal(case)
    findings = sweep(dirtied, world.now())

    reported = {f.appeal.appeal_id for f in findings}
    assert "appeal-50" in reported, "the day-150 appeal must still be reported"
    assert len(findings) == len(dirtied.appeals)


def test_the_appeal_it_cannot_read_is_raised_rather_than_dropped(case, world):
    """Unreadable is not the same as fine. Quietly omitting it would be the same
    silence by a tidier route."""
    dirtied = _with_a_disability_appeal(case)
    odd = next(f for f in sweep(dirtied, world.now())
               if f.appeal.appeal_id == "appeal-ltd")

    assert odd.needs_raising is True
    assert odd.unreadable_because
    assert "60 days" in odd.unreadable_because
    assert "cannot work out the deadlines" in odd.sentence


def test_the_deadline_screen_still_answers(case, world):
    """`GET /api/deadlines` returned 500 and took the day-150 appeal with it."""
    app = create_app()
    state = app.state.recourse
    state.store._case.appeals.update(
        _with_a_disability_appeal(state.store.case).appeals
    )
    with TestClient(app) as client:
        response = client.get("/api/deadlines")

    assert response.status_code == 200
    assert any(row["appeal_id"] == "appeal-50" for row in response.json())
