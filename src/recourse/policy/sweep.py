"""The obligation to speak.

`deadline_at_risk` is not a tool guard. Nothing the agent is about to do triggers it,
which is exactly why it needs its own machinery: it fires when the agent is about to
do *nothing*, and doing nothing is the failure.

Every other rule in this system waits to be provoked by a tool call. A background
agent that only ever spoke when provoked would go quiet for the six months of a
180-day window and then be right about everything except the one thing that
mattered. So this sweep runs on a schedule, over the whole case file, and it is the
only part of the policy that can raise a question nobody asked it.

It is pure. It reads the case file and the clock and returns what it found; raising,
recording and escalating are the caller's, so the same function serves the PRESS
loop, the API and the tests without any of them needing a running agent.
"""

from __future__ import annotations

from datetime import date

from recourse.domain.case import CaseFile
from recourse.domain.clocks import deadlines_for, insurer_is_overdue, risk_for
from recourse.policy.finding import Finding
from recourse.domain.types import AutonomyLevel, DeadlineRisk
from recourse.policy.rules import THRESHOLDS

#: Ordered worst first. A screen or an escalation list that buried a missed window
#: under three warnings would be sorting by tidiness rather than by consequence.
_ORDER = {
    DeadlineRisk.MISSED: 0,
    DeadlineRisk.CRITICAL: 1,
    DeadlineRisk.APPROACHING: 2,
    DeadlineRisk.OK: 3,
}


def sweep(
    case_file: CaseFile,
    now: date,
    level: AutonomyLevel = AutonomyLevel.BALANCED,
) -> tuple[Finding, ...]:
    """Every open appeal that needs saying out loud, worst first.

    Closed appeals are skipped: an answered denial has no clock left to miss.
    """
    warn_days = THRESHOLDS[level].warn_days
    findings: list[Finding] = []

    for appeal in case_file.appeals.values():
        if not appeal.is_open:
            continue
        denial = case_file.denials.get(appeal.denial_id)
        claim = case_file.claim_for_line(denial.line_id) if denial else None
        plan = case_file.plans.get(appeal.plan_id)
        if claim is None or plan is None:
            # Unreadable rather than fine. The caller escalates it as unassessable
            # instead of quietly leaving an appeal out of the count.
            continue

        deadlines = deadlines_for(
            plan=plan, service_type=claim.service_type, stage=appeal.stage,
            stage_started_on=appeal.stage_started_on,
            # The plan's clock runs from the day the appeal was posted. Passing the
            # notice date here reported an insurer as months late answering an appeal
            # that had never been sent to them.
            filed_on=appeal.sent_on,
        )
        risk = risk_for(deadlines, now, warn_days)
        remaining = (deadlines.mine - now).days if deadlines.mine else None
        findings.append(Finding(
            appeal=appeal, deadlines=deadlines, risk=risk, days_remaining=remaining,
            insurer_overdue=insurer_is_overdue(deadlines, now, appeal.answered_on),
            _today=now,
        ))

    findings.sort(key=lambda f: (_ORDER[f.risk], f.days_remaining
                                 if f.days_remaining is not None else 10**6))
    return tuple(findings)


def raisable(findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """The subset a person must actually be told about."""
    return tuple(f for f in findings if f.needs_raising)
