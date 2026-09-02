"""The vocabulary.

`PlanType` has three members and only two of them ship. `ERISA_NON_HEALTH` exists so
that it can be refused loudly. Non-health ERISA plans allow a claimant 60 days to
appeal rather than 180 (29 CFR 2560.503-1 (h)(2)(i)), and a system that quietly fell
back to the health figure would tell someone they had four more months than the law
gives them. That is the one direction an error here must never take.

`Money` lives in `money.py`; import it from there.
"""

from __future__ import annotations

from enum import Enum


class PlanType(str, Enum):
    """Which body of rules governs the appeal.

    ERISA_NON_HEALTH is in scope only to be refused: see the module docstring.
    """

    ACA_MARKETPLACE = "aca_marketplace"
    ERISA_GROUP_HEALTH = "erisa_group_health"
    ERISA_NON_HEALTH = "erisa_non_health"


class ServiceType(str, Enum):
    """Which clock a claim runs on. Every deadline in the regulation forks here."""

    URGENT = "urgent"
    PRE_SERVICE = "pre_service"
    POST_SERVICE = "post_service"


class DenialClass(str, Enum):
    """What kind of refusal this is, read from the claim's own X12 code.

    The line that matters is CLINICAL against everything else. A clerical denial is
    a form problem an agent can genuinely prepare alone; a clinical one is the
    treating clinician's argument and nobody else's.

    UNASSESSABLE is what an unrecognised code produces. It is never a quiet "no
    action needed" - roughly a third of denials are coded "Other" with no reason
    listed, and the honest response to a reason the insurer declined to give is to
    say so and escalate.
    """

    CLERICAL = "clerical"
    AUTHORIZATION = "authorization"
    ELIGIBILITY = "eligibility"
    COVERAGE = "coverage"
    TIMELINESS = "timeliness"
    CLINICAL = "clinical"
    UNASSESSABLE = "unassessable"


class AppealStage(str, Enum):
    """How far an appeal has travelled.

    INTERNAL_2 exists because an ERISA plan may require up to two mandatory internal
    appeals before a civil action (29 CFR 2560.503-1 (c)(2)). ACA marketplace plans
    do not, so their appeals never occupy this stage.
    """

    INTERNAL_1 = "internal_1"
    INTERNAL_2 = "internal_2"
    EXTERNAL = "external"
    CIVIL_ACTION = "civil_action"


class Outcome(str, Enum):
    PENDING = "pending"
    OVERTURNED = "overturned"
    PARTLY_OVERTURNED = "partly_overturned"
    UPHELD = "upheld"


class DeadlineRisk(str, Enum):
    """How close a clock is to running out.

    MISSED is terminal and never softens back to APPROACHING: the merits of an
    appeal filed late stop mattering, and a screen that downgraded that to a warning
    would be lying about the only unrecoverable state in this domain.
    """

    OK = "ok"
    APPROACHING = "approaching"
    CRITICAL = "critical"
    MISSED = "missed"


class AutonomyLevel(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    TRUSTED = "trusted"


class DecisionOutcome(str, Enum):
    APPROVE = "approve"
    DECLINE = "decline"
