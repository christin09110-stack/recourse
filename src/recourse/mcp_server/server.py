"""Recourse's engine, served over MCP.

The code table and the clocks are the most reusable part of this project and the
safest to expose: deterministic, side-effect free, no credentials, no model in the
path. Somebody with their own software can take the reasoning without taking the app,
and a claimant's agent can find out what CARC 197 means and how long they have left.

**Read-only, deliberately.** Nothing here drafts a letter, opens an appeal, files
anything or touches a case file. There is no such tool at any autonomy level, and
`tests/mcp/` asserts that rather than trusting this paragraph. Filing an appeal is a
legal act taken in a patient's name; a protocol that let a stranger's agent take it
would be a different and much worse product.

An unknown plan type or an unreadable code is an error here, not a free answer. The
loader refuses a plan type it has no clock table for — a non-health ERISA plan allows
60 days rather than 180 — and that refusal travels over the wire intact.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from recourse.mcp_server.tools_clocks import add_clock_tools
from recourse.mcp_server.tools_lookup import add_lookup_tools


def build_server() -> FastMCP:
    """The five read-only tools, and nothing else."""
    server = FastMCP("recourse")
    add_lookup_tools(server)
    add_clock_tools(server)
    return server


def main() -> None:
    """`recourse-mcp`. Speaks stdio, which is what an MCP client launches."""
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
