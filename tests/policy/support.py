"""Shared fixtures for the policy tests.

The Strands event is a `SimpleNamespace` rather than the SDK's own type: the handler
reads two keys off `tool_use` and nothing else, and building the real event would
test the SDK instead of the boundary.
"""

from datetime import date
from types import SimpleNamespace
from typing import Any

from recourse.domain.case import CaseFile
from recourse.domain.models import Document
from recourse.policy.citation import CitationGuard


def tool_event(tool_name: str, tool_use_id: str = "tu-1", **args: Any) -> SimpleNamespace:
    return SimpleNamespace(
        tool_use={"name": tool_name, "input": args, "toolUseId": tool_use_id},
    )


def said(text: str, *, clinical: Any = True, document_id: str | None = None) -> dict[str, Any]:
    """One assertion in the shape a model sends it: JSON, not an `Assertion`."""
    return {"text": text, "clinical": clinical, "document_id": document_id}


def case_with(*document_ids: str, appeals: tuple[Any, ...] = ()) -> CaseFile:
    case = CaseFile(case_id="case-1")
    for document_id in document_ids:
        case.documents[document_id] = Document(
            document_id=document_id, kind="clinical_note",
            title="Letter of medical necessity", received_on=date(2026, 3, 1),
        )
    for appeal in appeals:
        case.appeals[appeal.appeal_id] = appeal
    return case


def guard_over(case: CaseFile) -> CitationGuard:
    return CitationGuard(lambda: case)
