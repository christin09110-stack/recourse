"""Every model call and tool call, written by hooks on the agent loop.

Hooks rather than the agent reporting on itself. An appeal is an argument with an
institution that keeps its own record, and the claimant's account is worth something
only if it was written as things happened. An agent's summary of what it did is
exactly the thing that must not be trusted when the record is the defence — so the
record is taken from the loop, beside the agent, and the agent is never asked.

`record` is public so the interventions can write a refusal into the same trail: a
`Deny` that never reached a tool leaves no `BeforeToolCallEvent` behind it, and a
refusal absent from the log reads as a thing that never happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent, BeforeModelCallEvent, BeforeToolCallEvent


@dataclass(frozen=True)
class TrailEntry:
    kind: str
    label: str
    at: datetime
    detail: dict[str, Any] = field(default_factory=dict)


class AuditTrail(HookProvider):
    """One trail per run. Two runs sharing an instance interleave two case files."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._entries: list[TrailEntry] = []
        # The world's clock, not the wall's. Everything else on screen — the
        # journal, the countdowns, the notice dates — runs on the frozen demo
        # clock, and a trail stamped from the real one made two halves of the same
        # screen disagree about what day it was.
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeModelCallEvent, self._on_model)
        registry.add_callback(BeforeToolCallEvent, self._on_tool)
        registry.add_callback(AfterToolCallEvent, self._on_result)

    def record(self, kind: str, label: str, detail: dict[str, Any] | None = None) -> None:
        self._entries.append(TrailEntry(kind, label, self._clock(), dict(detail or {})))

    def entries(self) -> list[TrailEntry]:
        return list(self._entries)

    def of_kind(self, kind: str) -> list[TrailEntry]:
        return [entry for entry in self._entries if entry.kind == kind]

    def _on_model(self, event: Any) -> None:
        self.record("model_call", "reasoning")

    def _on_tool(self, event: Any) -> None:
        # The arguments, not a summary of them. "drafted a letter" is not a record;
        # which denial, with which assertions, citing which documents, is.
        self.record("tool_call", event.tool_use["name"], dict(event.tool_use.get("input", {})))

    def _on_result(self, event: Any) -> None:
        self.record("tool_result", event.tool_use["name"])
