"""The MCP surface: exactly five tools, and none of them writes.

The safety claim in the module docstring is asserted here rather than believed. A
protocol that let a stranger's agent draft, file or alter somebody's appeal would be
a different and much worse product, and the way that gets shipped by accident is a
convenience tool added later by someone who did not read the docstring.
"""

from __future__ import annotations

from recourse.domain.codes import classify
from recourse.mcp_server.server import build_server

from .conftest import payload as _payload, rows

THE_FIVE = {
    "classify_denial", "deadlines_for", "plan_rules", "evidence_required", "check_risk",
}

#: Anything that would change a case file, a person's record, or the world.
WRITE_WORDS = (
    "draft", "file", "submit", "send", "open", "advance", "record", "request",
    "create", "update", "delete", "notify", "answer", "set", "add", "write",
)


async def test_the_server_exposes_exactly_the_five_read_tools():
    tools = {t.name for t in await build_server().list_tools()}
    assert tools == THE_FIVE


async def test_no_exposed_tool_can_change_anybodys_case():
    for tool in await build_server().list_tools():
        assert not any(word in tool.name for word in WRITE_WORDS), tool.name


async def test_every_tool_has_a_description_a_stranger_can_act_on():
    for tool in await build_server().list_tools():
        assert tool.description and len(tool.description) > 40, tool.name


async def test_classifying_over_mcp_agrees_with_the_domain_function():
    server = build_server()
    for carc, rarc in [(["16"], ["N290"]), (["50"], []), (["197"], []), (["96"], [])]:
        result = await server.call_tool("classify_denial", {"carc": carc, "rarc": rarc})
        payload = _payload(result)
        assert payload["denial_class"] == classify(tuple(carc), tuple(rarc)).denial_class.value


async def test_an_unknown_code_is_unassessable_and_says_which_code():
    payload = _payload(await build_server().call_tool(
        "classify_denial", {"carc": ["ZZ9"], "rarc": []},
    ))
    assert payload["denial_class"] == "unassessable"
    assert payload["unknown_codes"] == ["ZZ9"]
    assert payload["assessable"] is False


async def test_a_code_row_carries_the_x12_url_it_was_read_from():
    payload = _payload(await build_server().call_tool(
        "classify_denial", {"carc": ["197"], "rarc": []},
    ))
    assert payload["matched"]["citation"].startswith("https://x12.org/")


async def test_evidence_required_names_the_one_document_only_a_clinician_can_write():
    served = rows(await build_server().call_tool(
        "evidence_required", {"denial_class": "clinical"},
    ))
    assert [row["kind"] for row in served] == ["clinical_note"]
