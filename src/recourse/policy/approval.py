"""What counts as a person saying yes.

Split out of `escalation.py` only for size; it is part of the same boundary and
`EscalationPolicy` hands it to every `Confirm` it raises.
"""

from __future__ import annotations

from typing import Any

#: Responses that mean the person said yes, as free text.
_APPROVING_WORDS = frozenset({"approve", "approved", "yes", "y", "true"})


def approves(response: Any) -> bool:
    """Whether a human's answer to a Confirm means "go ahead".

    Strands' `default_evaluate` accepts only `True` or the string "yes". Recourse
    answers with a structured record instead — the outcome, who decided, their
    relationship to the patient and their note — because every one of those fields
    ends up on the receipt.

    In Muster, which answers the same way, that record evaluated as "not approved":
    the operator pressed Approve, the run resumed, the same tool call was refused
    again, the agent retried, and the policy raised an identical question. Approving
    produced a fresh copy of the question it was answering.
    """
    if isinstance(response, dict):
        # The API answers with "outcome"; the SDK's own examples use "decision".
        # Accept either rather than depending on which a caller sends, because
        # getting it wrong does not fail loudly — it silently reads as a refusal and
        # the person's Approve turns into another identical question. Only these two
        # keys count: an unrecognised shape is a no, never a yes by accident.
        for key in ("outcome", "decision"):
            if key in response:
                return str(response[key]).strip().lower() in _APPROVING_WORDS
        return False
    if response is True:
        return True
    if isinstance(response, str):
        return response.strip().lower() in _APPROVING_WORDS
    return False
