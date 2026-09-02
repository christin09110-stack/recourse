"""The three lookup tools: what a code means, what a plan allows, what an appeal needs.

Each docstring is the tool's description over the wire, so it is written for a
stranger's agent that has never seen this codebase and has to decide from the text
alone whether the tool answers its question.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from recourse.mcp_server import lookups


def add_lookup_tools(server: FastMCP) -> None:
    @server.tool()
    def classify_denial(carc: list[str], rarc: list[str] | None = None) -> dict[str, Any]:
        """What kind of refusal a denied claim line is, read from its own X12 codes:
        clerical, authorization, eligibility, coverage, timeliness or clinical. An
        unrecognised code returns `unassessable` and never a guess. Returns the code
        row that produced the class, any remark code that narrowed it, and the X12
        source URL for both."""
        return lookups.classification(carc, rarc or [])

    @server.tool()
    def plan_rules(plan_type: str) -> dict[str, Any]:
        """The full clock table a plan type carries, every figure with the .gov URL it
        was read from: time to appeal, initial-notice periods, decision periods for
        one and for two mandatory internal levels, external review, and what follows
        exhaustion. `plan_type` is `aca_marketplace` or `erisa_group_health`. A plan
        type with no table is refused rather than defaulted to a health plan's."""
        return lookups.plan_rules(plan_type)

    @server.tool()
    def evidence_required(denial_class: str) -> list[dict[str, Any]]:
        """The documents a credible appeal of this class of denial needs, and what
        each one establishes. `denial_class` is one of the values `classify_denial`
        returns. Required entries are the ones without which the appeal is not
        credible; the rest merely strengthen it."""
        return lookups.requirements(denial_class)
