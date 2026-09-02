"""The demo clock, and every offset the seeded world is built from.

A recorded demo of a countdown is only honest if the countdown is reproducible.
Everything in the seeded world is therefore stated as *days before* one fixed date
rather than as a literal calendar date, so the figures on screen in a recording are
the same figures a year later, and so the two clock situations the demo turns on
cannot drift apart from the dates that produce them.

The offsets are named rather than inlined because two of them are the demo:
`DAYS_INTO_FILING_WINDOW` puts one appeal at day 150 of its 180, and
`_ACA_POST_SERVICE_DECISION_DAYS + INSURER_OVERDUE_BY` puts another insurer 19 days
past its own limit to answer. The 60 is copied from the rulebook rather than read
from it, to keep the seed free of a load-time dependency on the loader; the adapter
tests cross-check it against `deadlines_for`, so a change to the rulebook fails the
suite instead of quietly moving the demo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

#: 2 September 2026 — the date the design's figures were fetched.
FROZEN_TODAY: date = date(2026, 9, 2)

#: The same instant, for anything that stamps a timestamp rather than a date.
FROZEN_NOW: datetime = datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)

#: Day 150 of the 180-day window to file an internal appeal. With `warn_days=30`
#: that is exactly the boundary at which `risk_for` reports APPROACHING, which is
#: the point: the demo shows the warning at the moment it is first earned.
DAYS_INTO_FILING_WINDOW = 150

#: How far past its own deadline the silent insurer is.
INSURER_OVERDUE_BY = 19

#: An ACA marketplace plan has 60 days to decide a post-service appeal
#: (healthcare.gov, internal appeals). Mirrored here; asserted in the tests.
_ACA_POST_SERVICE_DECISION_DAYS = 60

#: The plan's clock runs from the day the appeal was *posted*, not from its own
#: denial notice, so this is how long ago it was sent. Deriving it from the notice
#: date reported an insurer as late answering a letter nobody had sent yet.
DAYS_SINCE_APPEAL_SENT = _ACA_POST_SERVICE_DECISION_DAYS + INSURER_OVERDUE_BY

#: The denial came a week before the claimant got round to appealing it.
DAYS_SINCE_UNANSWERED_NOTICE = DAYS_SINCE_APPEAL_SENT + 7


def ago(days: int) -> date:
    """A date `days` before the frozen today."""
    return FROZEN_TODAY - timedelta(days=days)
