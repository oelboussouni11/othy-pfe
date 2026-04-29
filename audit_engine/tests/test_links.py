"""Link audit tests."""

import pytest
from pytest_httpserver import HTTPServer

from audit_engine.checks.links import audit_links
from audit_engine.types import CrawledPage, Severity


def _page(url: str, html: str) -> CrawledPage:
    return CrawledPage(url=url, status_code=200, html=html, response_time_ms=10)


@pytest.mark.asyncio
async def test_broken_link_is_flagged_as_critical(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/missing").respond_with_data("nope", status=404)

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/missing")}">m</a>')]
    issues = await audit_links(pages)

    assert len(issues) == 1
    assert issues[0].severity == Severity.critical
    assert issues[0].type == "client_error"
    assert issues[0].status_code == 404


@pytest.mark.asyncio
async def test_server_error_is_flagged_as_critical(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/down").respond_with_data("ouch", status=503)

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/down")}">d</a>')]
    issues = await audit_links(pages)

    assert issues[0].severity == Severity.critical
    assert issues[0].type == "server_error"


@pytest.mark.asyncio
async def test_temporary_redirect_is_warn(httpserver: HTTPServer) -> None:
    final = httpserver.url_for("/final")
    httpserver.expect_request("/temp").respond_with_data(
        "", status=302, headers={"Location": final}
    )
    httpserver.expect_request("/final").respond_with_data("ok", content_type="text/html")

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/temp")}">t</a>')]
    issues = await audit_links(pages)

    types = {i.type for i in issues}
    assert "temporary_redirect" in types
    assert any(i.severity == Severity.warning for i in issues if i.type == "temporary_redirect")


@pytest.mark.asyncio
async def test_permanent_redirect_is_info(httpserver: HTTPServer) -> None:
    final = httpserver.url_for("/final2")
    httpserver.expect_request("/perm").respond_with_data(
        "", status=301, headers={"Location": final}
    )
    httpserver.expect_request("/final2").respond_with_data("ok", content_type="text/html")

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/perm")}">p</a>')]
    issues = await audit_links(pages)

    perm = [i for i in issues if i.type == "permanent_redirect"]
    assert perm
    assert perm[0].severity == Severity.info


@pytest.mark.asyncio
async def test_long_redirect_chain_is_warn(httpserver: HTTPServer) -> None:
    final = httpserver.url_for("/final")
    httpserver.expect_request("/r1").respond_with_data(
        "", status=301, headers={"Location": httpserver.url_for("/r2")}
    )
    httpserver.expect_request("/r2").respond_with_data(
        "", status=301, headers={"Location": httpserver.url_for("/r3")}
    )
    httpserver.expect_request("/r3").respond_with_data("", status=301, headers={"Location": final})
    httpserver.expect_request("/final").respond_with_data("ok", content_type="text/html")

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/r1")}">r</a>')]
    issues = await audit_links(pages)

    chain_issues = [i for i in issues if i.type == "long_redirect_chain"]
    assert chain_issues
    assert chain_issues[0].severity == Severity.warning


@pytest.mark.asyncio
async def test_ok_links_are_not_reported(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/healthy").respond_with_data("ok", content_type="text/html")

    pages = [_page(httpserver.url_for("/"), f'<a href="{httpserver.url_for("/healthy")}">h</a>')]
    issues = await audit_links(pages)

    assert issues == []


@pytest.mark.asyncio
async def test_anchor_dedup_per_link(httpserver: HTTPServer) -> None:
    """Same broken link cited from multiple pages should yield one issue per page."""
    httpserver.expect_request("/missing").respond_with_data("nope", status=404)

    pages = [
        _page("https://x.test/a", f'<a href="{httpserver.url_for("/missing")}">m</a>'),
        _page("https://x.test/b", f'<a href="{httpserver.url_for("/missing")}">m</a>'),
    ]
    issues = await audit_links(pages)
    assert len(issues) == 2
    assert {i.page_url for i in issues} == {"https://x.test/a", "https://x.test/b"}


@pytest.mark.asyncio
async def test_pages_without_html_are_skipped() -> None:
    pages = [CrawledPage(url="https://x.test/", status_code=0, html="", response_time_ms=0)]
    assert await audit_links(pages) == []
