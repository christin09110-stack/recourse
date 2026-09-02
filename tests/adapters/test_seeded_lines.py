# tests/adapters/test_seeded_lines.py
"""The partial denial, and the cost-share noise it has to be told apart from."""

from __future__ import annotations

from recourse.domain.money import Money

COST_SHARE = {"1", "2", "3"}


def test_a_partial_denial_is_seeded_and_reads_as_denied(case):
    """The plan paid eight physiotherapy visits and refused four. Reading denial as
    payment-of-zero hid exactly this shape, so the demo has to contain one."""
    line = case.line("line-physio-visits")
    assert line.plan_paid > Money.zero()
    assert line.is_partial_denial is True
    assert line.is_denied is True
    assert case.denials["den-96"].line_id == line.line_id


def test_a_cost_share_only_line_is_not_a_denial(case):
    line = case.line("line-physio-eval")
    assert set(line.carc) <= COST_SHARE
    assert line.adjustment_codes == ()
    assert line.is_denied is False


def test_the_noise_lines_are_present_and_none_of_them_became_a_denial(case):
    noisy = [
        line for claim in case.claims.values() for line in claim.lines
        if line.carc and set(line.carc) <= COST_SHARE
    ]
    assert len(noisy) >= 2
    denied_line_ids = {denial.line_id for denial in case.denials.values()}
    assert not denied_line_ids & {line.line_id for line in noisy}


def test_every_denied_line_has_a_denial_and_nothing_else_does(case):
    denied = {
        line.line_id for claim in case.claims.values() for line in claim.denied_lines
    }
    assert denied == {denial.line_id for denial in case.denials.values()}


def test_the_world_rebuilds_identically_from_its_seed(world):
    """`POST /api/demo/reset` has to give the recording back its opening state."""
    before = world.case_file()
    world.reset()
    after = world.case_file()
    assert before is not after
    assert before == after
