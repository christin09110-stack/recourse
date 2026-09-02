"""Reading a tool result back.

`call_tool` in mcp 1.x returns a (content, payload) pair rather than the payload
alone, and a list-returning tool arrives wrapped in {"result": [...]}. Both shapes
are the protocol's, not ours, so unwrapping lives here instead of in every test.
"""

from __future__ import annotations

from typing import Any


def payload(result: Any) -> Any:
    return result[1] if isinstance(result, tuple) else result


def rows(result: Any) -> Any:
    """A list-returning tool's rows, however this mcp version wrapped them."""
    body = payload(result)
    return body["result"] if isinstance(body, dict) and "result" in body else body
