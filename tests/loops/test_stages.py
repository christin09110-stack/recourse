"""Which door is next after an upheld appeal, and for which plan.

An upheld internal appeal does not always go to external review, and this is the fork
worth getting right: telling somebody to file for an external review their plan does
not offer sends them to a process that will not accept them, and telling somebody
they must sue when a free binding review was available is worse.
"""

from __future__ import annotations

from dataclasses import replace

from recourse.adapters.seed_plans import PLAN_ERISA
from recourse.domain.types import AppealStage, Outcome
from tests.loops.support import press

ANSWERED = "2026-09-01"


def test_an_upheld_aca_level_one_goes_to_external_review():
    store, tools, _ = press()
    recorded = tools["record_response"](appeal_id="appeal-16", outcome="upheld",
                                        answered_on=ANSWERED)
    assert recorded["next_stage"] == AppealStage.EXTERNAL.value
    assert "independent review organisation" in recorded["what_changes"]
    moved = tools["advance_stage"](appeal_id="appeal-16")
    assert moved["stage"] == AppealStage.EXTERNAL.value
    assert store.appeal("appeal-16").stage is AppealStage.EXTERNAL


def test_an_upheld_erisa_level_one_goes_to_a_second_internal_appeal_first():
    """Two mandatory internal levels means external review is not next, it is third."""
    store, tools, _ = press()
    recorded = tools["record_response"](appeal_id="appeal-197", outcome="upheld",
                                        answered_on=ANSWERED)
    assert recorded["next_stage"] == AppealStage.INTERNAL_2.value
    moved = tools["advance_stage"](appeal_id="appeal-197")
    assert moved["stage"] == AppealStage.INTERNAL_2.value
    # And only then external, said from the clocks recomputed after the move.
    assert moved["then"] == AppealStage.EXTERNAL.value
    assert store.appeal("appeal-197").history[0].outcome is Outcome.UPHELD


def test_a_grandfathered_plan_has_no_external_review_only_a_civil_action():
    """The ACA external-review right does not reach a grandfathered plan, so what is
    left after the internal levels is a lawsuit under ERISA 502(a) — a lawyer's
    question, and the point at which these clocks stop."""
    store, tools, _ = press()
    plan = store.case.plans[PLAN_ERISA]
    store.case.plans[PLAN_ERISA] = replace(plan, grandfathered=True, internal_levels=1)

    recorded = tools["record_response"](appeal_id="appeal-197", outcome="upheld",
                                        answered_on=ANSWERED)
    assert recorded["next_stage"] == AppealStage.CIVIL_ACTION.value
    assert "no external review" in recorded["what_changes"]
    assert tools["advance_stage"](appeal_id="appeal-197")["stage"] == \
        AppealStage.CIVIL_ACTION.value
