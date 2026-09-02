"""Fakes for the two loops, so the API can be tested without an agent.

Every runner is injected into `create_app`, which means these tests need no AWS
credential, no network and no model. The fakes are deliberately dumb: they return a
result shaped like `loops.run.LoopRunResult` and record that they were called.

`SpyRunner.calls` is the whole point of one of these tests. A decline must never
reach the resumer, and the only way to assert "never reached" is to have something
that would have noticed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from recourse.api.app import create_app


@dataclass
class FakeResult:
    """The shape `loops.run` returns, with nothing behind it."""

    paused: bool = False
    interrupt_id: str | None = None
    interrupt_reason: str | None = None
    snapshot: dict[str, Any] | None = None
    text: str = "done"
    rule_hits: list[dict[str, str]] = field(default_factory=list)
    proposal: dict[str, Any] = field(default_factory=dict)


def paused_on(denial_id: str = "den-50", rule: str = "uncited_clinical_assertion") -> FakeResult:
    """A run stopped by the policy, carrying the call it stopped on."""
    return FakeResult(
        paused=True,
        interrupt_id="v1:before_tool_call:tooluse_abc:1234",
        interrupt_reason=rule,
        snapshot={"messages": []},
        text="This would state something clinical that no document supports. Approve this?",
        rule_hits=[{"rule": rule, "detail": "nothing in the file supports it"}],
        proposal={"tool": "draft_letter_body", "denial_id": denial_id},
    )


class SpyRunner:
    """Records every call, so a test can assert one never happened."""

    def __init__(self, result: FakeResult | None = None) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.result = result if result is not None else FakeResult()

    async def __call__(self, *args: Any) -> FakeResult:
        self.calls.append(args)
        return self.result


def _unreachable(name: str) -> SpyRunner:
    """A runner no route under test should touch. Its calls are asserted empty."""
    return SpyRunner(FakeResult(text=f"{name} should not have run"))


@pytest.fixture
def client() -> TestClient:
    """The API with both loops stubbed out and no run ever paused."""
    return TestClient(create_app(
        watch_runner=_unreachable("watch"),
        press_runner=_unreachable("press"),
        decision_resumer=_unreachable("resume"),
    ))
