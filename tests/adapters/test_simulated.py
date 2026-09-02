# tests/adapters/test_simulated.py
"""The three denials that are the demo, and the two clocks it turns on."""

from __future__ import annotations

from datetime import date

from recourse.adapters.frozen import DAYS_INTO_FILING_WINDOW, INSURER_OVERDUE_BY
from recourse.domain.clocks import insurer_is_overdue, risk_for
from recourse.domain.code_table import lookup
from recourse.domain.codes import classify
from recourse.domain.evidence import can_prepare_alone, gaps
from recourse.domain.types import DeadlineRisk, DenialClass, PlanType

from tests.adapters.conftest import deadlines_of

WARN_DAYS = 30


def test_the_clock_is_frozen_so_every_countdown_is_reproducible(world):
    assert world.now() == date(2026, 9, 2)


def test_the_household_holds_one_marketplace_plan_and_one_two_level_erisa_plan(case):
    kinds = {p.plan_type: p for p in case.plans.values()}
    assert kinds[PlanType.ACA_MARKETPLACE].internal_levels == 1
    assert kinds[PlanType.ERISA_GROUP_HEALTH].internal_levels == 2
    assert kinds[PlanType.ERISA_GROUP_HEALTH].grandfathered is False


def test_every_denials_codes_exist_in_the_table_and_classify_as_stated(case):
    stated = {
        "den-16": DenialClass.CLERICAL,
        "den-197": DenialClass.AUTHORIZATION,
        "den-50": DenialClass.CLINICAL,
        "den-96": DenialClass.COVERAGE,
    }
    assert set(case.denials) == set(stated)
    for denial_id, denial_class in stated.items():
        denial = case.denials[denial_id]
        line = case.line(denial.line_id)
        for code in line.carc:
            assert lookup("CARC", code) is not None, code
        for code in line.rarc:
            assert lookup("RARC", code) is not None, code
        assert classify(line.carc, line.rarc).denial_class is denial_class
        # The seed must never label a denial something the engine would contradict.
        assert denial.denial_class is denial_class


def test_the_clerical_denial_can_be_prepared_from_the_eob_alone(case):
    assert gaps(case, DenialClass.CLERICAL) == ()
    assert can_prepare_alone(case, DenialClass.CLERICAL) is True


def test_the_authorisation_approval_is_already_in_the_file_and_nothing_is_missing(case):
    """The one that lands on camera: the approval existed all along."""
    approvals = case.documents_of_kind("authorization")
    assert len(approvals) == 1
    mri = case.line(case.denials["den-197"].line_id)
    # And it was granted before the scan, not reconstructed afterwards.
    assert approvals[0].received_on < mri.service_date
    assert gaps(case, DenialClass.AUTHORIZATION) == ()
    assert can_prepare_alone(case, DenialClass.AUTHORIZATION) is True


def test_the_clinical_denial_names_its_missing_letter_and_is_handed_back(case):
    assert case.documents_of_kind("clinical_note") == ()
    missing = gaps(case, DenialClass.CLINICAL)
    assert [req.kind for req in missing] == ["clinical_note"]
    assert can_prepare_alone(case, DenialClass.CLINICAL) is False


def test_one_appeal_really_is_at_day_150_of_its_180_and_reads_approaching(case, world):
    appeal = case.appeals["appeal-50"]
    elapsed = (world.now() - appeal.stage_started_on).days
    assert elapsed == DAYS_INTO_FILING_WINDOW == 150
    clocks = deadlines_of(case, appeal)
    assert (clocks.mine - world.now()).days == 180 - 150
    assert risk_for(clocks, world.now(), WARN_DAYS) is DeadlineRisk.APPROACHING


def test_one_insurer_really_is_19_days_past_its_own_deadline_to_answer(case, world):
    appeal = case.appeals["appeal-16"]
    clocks = deadlines_of(case, appeal)
    assert appeal.answered_on is None
    assert (world.now() - clocks.theirs).days == INSURER_OVERDUE_BY == 19
    assert insurer_is_overdue(clocks, world.now(), appeal.answered_on) is True
