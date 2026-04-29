"""Crawler tests using a live in-process HTTP server (pytest-httpserver)."""

import pytest
from pytest_httpserver import HTTPServer

from audit_engine.crawler import CrawlConfig, crawl


def _html(body: str) -> tuple[str, dict]:
    return body, {"content_type": "text/html"}


@pytest.mark.asyncio
async def test_crawler_finds_all_pages_via_links(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<a href="/about">a</a><a href="/contact">c</a>',
        content_type="text/html",
    )
    httpserver.expect_request("/about").respond_with_data("about", content_type="text/html")
    httpserver.expect_request("/contact").respond_with_data("c", content_type="text/html")

    pages = await crawl(httpserver.url_for("/"), CrawlConfig(respect_robots=False))

    paths = {p.url.replace(httpserver.url_for(""), "/").rstrip("/") or "/" for p in pages}
    assert paths == {"/", "/about", "/contact"}


@pytest.mark.asyncio
async def test_crawler_skips_external_links_when_same_origin_only(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<a href="https://example.com/external">ext</a><a href="/local">l</a>',
        content_type="text/html",
    )
    httpserver.expect_request("/local").respond_with_data("local", content_type="text/html")

    pages = await crawl(httpserver.url_for("/"), CrawlConfig(respect_robots=False))

    urls = [p.url for p in pages]
    assert not any("example.com" in u for u in urls)


@pytest.mark.asyncio
async def test_crawler_records_4xx_status(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<a href="/missing">m</a>', content_type="text/html"
    )
    httpserver.expect_request("/missing").respond_with_data("nope", status=404)

    pages = await crawl(httpserver.url_for("/"), CrawlConfig(respect_robots=False))
    by_status = {p.status_code for p in pages}
    assert 200 in by_status
    assert 404 in by_status


@pytest.mark.asyncio
async def test_crawler_dedupes_links(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<a href="/a">x</a><a href="/a#frag1">y</a><a href="/a#frag2">z</a>',
        content_type="text/html",
    )
    httpserver.expect_request("/a").respond_with_data("a", content_type="text/html")

    pages = await crawl(httpserver.url_for("/"), CrawlConfig(respect_robots=False))
    paths = [p.url.split("/")[-1] or "root" for p in pages]
    assert paths.count("a") == 1


@pytest.mark.asyncio
async def test_crawler_respects_max_pages(httpserver: HTTPServer) -> None:
    # Page links to many others
    links = "".join(f'<a href="/p{i}">x</a>' for i in range(20))
    httpserver.expect_request("/").respond_with_data(links, content_type="text/html")
    for i in range(20):
        httpserver.expect_request(f"/p{i}").respond_with_data(
            f"page {i}", content_type="text/html"
        )

    pages = await crawl(
        httpserver.url_for("/"), CrawlConfig(respect_robots=False, max_pages=5)
    )
    assert len(pages) == 5


@pytest.mark.asyncio
async def test_crawler_respects_robots_txt(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/robots.txt").respond_with_data(
        "User-agent: *\nDisallow: /private\n", content_type="text/plain"
    )
    httpserver.expect_request("/").respond_with_data(
        '<a href="/public">p</a><a href="/private">q</a>',
        content_type="text/html",
    )
    httpserver.expect_request("/public").respond_with_data("public", content_type="text/html")

    pages = await crawl(httpserver.url_for("/"))
    urls = [p.url for p in pages]
    assert any("/public" in u for u in urls)
    assert not any("/private" in u for u in urls)


@pytest.mark.asyncio
async def test_crawler_parses_sitemap(httpserver: HTTPServer) -> None:
    base = httpserver.url_for("/")
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{base}a</loc></url>"
        f"<url><loc>{base}b</loc></url>"
        "</urlset>"
    )
    httpserver.expect_request("/sitemap.xml").respond_with_data(
        sitemap, content_type="application/xml"
    )
    httpserver.expect_request("/a").respond_with_data("A", content_type="text/html")
    httpserver.expect_request("/b").respond_with_data("B", content_type="text/html")

    pages = await crawl(httpserver.url_for("/sitemap.xml"), CrawlConfig(respect_robots=False))
    urls = [p.url for p in pages]
    assert any(u.endswith("/a") for u in urls)
    assert any(u.endswith("/b") for u in urls)
