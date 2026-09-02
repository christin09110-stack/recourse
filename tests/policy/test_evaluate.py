"""The dial, and the three rules that ignore it."""

from __future__ import annotations

import pytest

from recourse.domain.types import AutonomyLevel, DeadlineRisk
from recourse.policy.evaluate import evaluate
from recourse.policy.rules import NON_NEGOTIABLE_RULES, THRESHOLDS, ActionContext

LEVELS = list(AutonomyLevel)


def _ctx(**kw) -> ActionContext:
    return ActionContext(tool="draft_letter_body", **kw)


def _rules(context, level) -> set[str]:
    return {hit.rule for hit in evaluate(context, level)}


@pytest.mark.parametrize("level", LEVELS)
def test_an_uncited_clinical_claim_is_refused_at_every_level(level):
    hits = _rules(_ctx(uncited_clinical=("Symptoms since March.",)), level)
    assert "uncited_clinical_assertion" in hits


@pytest.mark.parametrize("level", LEVELS)
def test_filing_is_never_the_agents_at_any_level(level):
    assert "filing_is_not_the_agents" in _rules(_ctx(would_file=True), level)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("risk", [DeadlineRisk.APPROACHING, DeadlineRisk.CRITICAL,
                                  DeadlineRisk.MISSED])
def test_a_deadline_at_risk_is_raised_at_every_level(level, risk):
    assert "deadline_at_risk" in _rules(_ctx(risk=risk, days_remaining=12), level)


def test_the_three_non_negotiables_are_exactly_what_the_rules_declare():
    assert NON_NEGOTIABLE_RULES == {
        "uncited_clinical_assertion", "filing_is_not_the_agents", "deadline_at_risk",
    }


def test_a_missed_deadline_says_the_merits_stopped_mattering():
    """A person reading this should understand the consequence without a rule code."""
    hit = next(h for h in evaluate(_ctx(risk=DeadlineRisk.MISSED),
                                   AutonomyLevel.TRUSTED) if h.rule == "deadline_at_risk")
    assert "merits" in hit.detail


def test_even_conservative_warns_early_about_a_closing_window():
    """The dial governs what the agent does. Warning is not doing anything to
    anybody, and a setting that made it quieter would make it useless."""
    assert THRESHOLDS[AutonomyLevel.CONSERVATIVE].warn_days >= 30


def test_an_overdue_insurer_is_reported_even_when_nothing_else_is_wrong():
    assert "insurer_overdue" in _rules(_ctx(insurer_overdue=True), AutonomyLevel.TRUSTED)


def test_a_records_request_needs_a_person_below_trusted():
    assert "records_request_needs_you" in _rules(
        _ctx(reaches_a_third_party=True), AutonomyLevel.BALANCED)
    assert "records_request_needs_you" not in _rules(
        _ctx(reaches_a_third_party=True), AutonomyLevel.TRUSTED)


def test_conservative_does_not_draft_unprompted_and_balanced_does():
    assert "draft_needs_you" in _rules(_ctx(unprompted_draft=True),
                                       AutonomyLevel.CONSERVATIVE)
    assert "draft_needs_you" not in _rules(_ctx(unprompted_draft=True),
                                           AutonomyLevel.BALANCED)


def test_an_unreadable_world_stops_everything_and_nothing_else_is_reported():
    """Unknown is never benign, and it is not mixed in with ordinary findings."""
    hits = evaluate(_ctx(assessable=False, risk=DeadlineRisk.CRITICAL), AutonomyLevel.TRUSTED)
    assert [h.rule for h in hits] == ["unassessable"]


def test_a_clean_action_at_a_permissive_level_trips_nothing():
    assert _rules(_ctx(), AutonomyLevel.TRUSTED) == set()
