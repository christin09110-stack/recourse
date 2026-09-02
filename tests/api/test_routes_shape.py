"""The shape of the route table itself, checked without a browser.

`/api/api/...` is unreachable from a console whose BASE is already `/api`, and a
static file mount answers 405 rather than 404 for a path it does not have — so the
console reported a method problem for a route that was simply not there. curl never
caught it, because curl was typing the right path by hand.
"""

from __future__ import annotations


def test_the_timeline_is_the_audit_trail(client):
    assert client.get("/api/timeline").json() == []


def test_the_reset_route_is_a_post_and_only_a_post(client):
    """The path the console actually calls, exercised as the console calls it."""
    assert client.post("/api/demo/reset").status_code == 200
    assert client.get("/api/demo/reset").status_code == 405


def test_no_route_repeats_the_api_prefix(client):
    """`/api/api/...` is unreachable from a console whose BASE is already `/api`."""
    doubled = [r.path for r in client.app.routes if r.path.startswith("/api/api")]
    assert not doubled, doubled
