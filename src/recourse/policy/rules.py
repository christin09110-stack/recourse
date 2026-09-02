"""Where Recourse's authority ends, as executable code.

The dial moves ordinary things: how early it warns about a deadline, whether it may
ask a provider for records in the claimant's name, whether it may draft unprompted.

**Three rules ignore the dial completely**, and two of them are the shape you would
expect — prohibitions. The third is not.

`uncited_clinical_assertion` — an appeal may not state a symptom, a diagnosis or a
course of treatment that no document in the file supports. That is not a weak appeal;
it is a false statement on an insurance document, made in the patient's name.

`filing_is_not_the_agents` — no tool in this system files an appeal, and this rule
exists to refuse anything that tries. Submitting is a legal act taken in someone
else's name; the agent prepares and a person sends.

`deadline_at_risk` — a **duty**. It fires because the agent must act, not because it
must not. Everywhere else a guardrail stops the agent doing something; here silence
is the failure, and an unanswered deadline escalation gets louder rather than going
quiet. Fewer than 1% of denied claims are ever appealed, and the reason is not that
people accept the decision. It is that nobody told them the clock was running.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.domain.types import AutonomyLevel, DeadlineRisk


@dataclass(frozen=True)
class Thresholds:
    """What the dial actually moves."""

    #: Days before the claimant's own deadline at which it starts raising it.
    warn_days: int
    #: May it write a draft without being asked?
    may_draft_unprompted: bool
    #: May it ask a provider or plan for records in the claimant's name?
    may_request_records: bool


THRESHOLDS: dict[AutonomyLevel, Thresholds] = {
    # Conservative still warns early. The dial governs what the agent *does*, and
    # warning is not doing anything to anybody: a setting that made it quieter about
    # a closing deadline would be a setting that made it useless.
    AutonomyLevel.CONSERVATIVE: Thresholds(30, False, False),
    AutonomyLevel.BALANCED: Thresholds(45, True, False),
    AutonomyLevel.TRUSTED: Thresholds(60, True, True),
}

#: Fire at every level. No setting loosens any of them.
NON_NEGOTIABLE_RULES: frozenset[str] = frozenset({
    "uncited_clinical_assertion",
    "filing_is_not_the_agents",
    "deadline_at_risk",
})


@dataclass(frozen=True)
class RuleHit:
    rule: str
    detail: str


@dataclass(frozen=True)
class ActionContext:
    """Everything the policy needs to judge one proposed action."""

    tool: str
    #: Clinical assertions with no supporting document in the case file.
    uncited_clinical: tuple[str, ...] = ()
    #: True for any tool that would submit rather than prepare.
    would_file: bool = False
    risk: DeadlineRisk = DeadlineRisk.OK
    days_remaining: int | None = None
    insurer_overdue: bool = False
    reaches_a_third_party: bool = False
    unprompted_draft: bool = False
    #: False when the world cannot be read well enough to judge at all.
    assessable: bool = True
