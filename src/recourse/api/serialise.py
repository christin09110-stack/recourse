"""The record, as JSON the console can render without reinterpreting it.

Money crosses this boundary as `"1234.50"` — the string `Money.dollars` produces —
and never as a float or a cent count the browser would have to divide. A console
that does its own arithmetic on money is a second implementation of the thing this
codebase keeps in one place, and it is the copy that ends up in the letter.

Nothing here decides anything: a view that computed would be a second engine, and
the second engine is the one that ends up disagreeing with the letter.
"""

from __future__ import annotations

from typing import Any

from recourse.domain.models import Claim, ClaimLine, Document, Plan


def plan_view(plan: Plan) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "plan_type": plan.plan_type.value,
        "member_id": plan.member_id,
        "internal_levels": plan.internal_levels,
        "grandfathered": plan.grandfathered,
        "appeals_address": plan.appeals_address,
    }


def line_view(line: ClaimLine) -> dict[str, Any]:
    return {
        "line_id": line.line_id,
        "claim_id": line.claim_id,
        "description": line.description,
        "service_date": line.service_date.isoformat(),
        "provider": line.provider,
        "billed": line.billed.dollars,
        "allowed": line.allowed.dollars,
        "plan_paid": line.plan_paid.dollars,
        "patient_responsibility": line.patient_responsibility.dollars,
        "carc": list(line.carc),
        "rarc": list(line.rarc),
        # Both, because they answer different questions: `carc` is what the EOB
        # printed, `adjustment_codes` is what actually refused something. Codes 1-3
        # are deductible, coinsurance and copay, and a screen that read those as
        # denials would raise three false alarms on the seeded file alone.
        "adjustment_codes": list(line.adjustment_codes),
        "is_denied": line.is_denied,
        "is_partial_denial": line.is_partial_denial,
        "needs_review": line.needs_review,
    }


def claim_view(claim: Claim) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "plan_id": claim.plan_id,
        "provider": claim.provider,
        "service_type": claim.service_type.value,
        "notice_date": claim.notice_date.isoformat(),
        "denied_total": claim.denied_total.dollars,
        "lines": [line_view(line) for line in claim.lines],
    }


def document_view(document: Document) -> dict[str, Any]:
    return {
        "document_id": document.document_id,
        "kind": document.kind,
        "title": document.title,
        "received_on": document.received_on.isoformat(),
    }
