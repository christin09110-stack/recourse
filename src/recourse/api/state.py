"""Process-wide state for the control plane, and the one function that builds it.

Everything the API serves hangs off a single `RecourseState` on `app.state.recourse`.
There is no database: this build holds the case file, the inbox, the journal and the
audit trail in memory and says so rather than implying durability it does not have.

`build_state` is the *only* way to make one, and start-up and `POST /api/demo/reset`
both call it. That is not tidiness. Muster's reset built its state a second way and
forgot the seeded postings the guards read, which produced a console where every
control was refused and nothing said why. A reset that does not reproduce a cold
start is worse than no reset at all, because it looks like one.
"""

from __future__ import annotations

from dataclasses import dataclass

from recourse.adapters.simulated import SimulatedWorld
from recourse.domain.case import CaseFile
from recourse.domain.types import AutonomyLevel
from recourse.hooks.audit import AuditTrail
from recourse.persistence.inbox import DecisionInbox
from recourse.persistence.journal import Journal
from recourse.persistence.store import CaseStore


@dataclass
class RecourseState:
    """The demo world, the case file, and everything written about them."""

    world: SimulatedWorld
    store: CaseStore
    inbox: DecisionInbox
    journal: Journal
    trail: AuditTrail
    autonomy: AutonomyLevel = AutonomyLevel.BALANCED

    @property
    def case(self) -> CaseFile:
        """The live case file. The store owns it; nothing else may reseat it."""
        return self.store.case


def build_state(autonomy: AutonomyLevel = AutonomyLevel.BALANCED) -> RecourseState:
    """A cold start: the seeded world, and the journal a cold start would hold."""
    world = SimulatedWorld()
    state = RecourseState(
        world=world,
        # Over the world's own case file object, so a document added through the
        # store is the same document the world hands to `evidence.gaps`.
        store=CaseStore(world.case_file()),
        inbox=DecisionInbox(),
        journal=Journal(),
        trail=AuditTrail(),
        autonomy=autonomy,
    )
    _record_seeded_history(state)
    return state


def _record_seeded_history(state: RecourseState) -> None:
    """Write the appeals the seeded world already has open into the journal.

    The demo world starts mid-story — three appeals already running, one of them at
    day 150 — because that is where a real household finds itself. Nothing had
    written those down, so the Journal screen opened empty beside a Deadlines screen
    with three live clocks on it, which reads as a record that lost the first five
    months of the case.
    """
    for appeal in sorted(state.case.appeals.values(), key=lambda a: a.appeal_id):
        opened = appeal.stage_started_on
        state.journal.write(
            kind="appeal_opened",
            sentence=(
                f"Appeal {appeal.appeal_id} was opened against denial "
                f"{appeal.denial_id}"
                + (f", counting from the notice of {opened:%d %B %Y}." if opened else ".")
            ),
            at=state.world.now_at(),
            appeal_id=appeal.appeal_id,
        )
