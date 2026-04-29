"""SEO audit tests — pure HTML, no network."""

from audit_engine.checks.seo import audit_seo
from audit_engine.types import CrawledPage, Severity


def _page(html: str) -> CrawledPage:
    return CrawledPage(url="https://x.test/", status_code=200, html=html, response_time_ms=10)


def _types(issues, page_url=None):
    if page_url:
        issues = [i for i in issues if i.page_url == page_url]
    return {i.type for i in issues}


# A nearly-perfect page used as a baseline.
GOOD_PAGE = """
<!doctype html>
<html><head>
  <title>SmartLaunch QA — pre-launch site auditing for serious teams</title>
  <meta name="description" content="SmartLaunch QA crawls staging and production, diffs them, and tells you go or no-go before you ship.">
  <link rel="canonical" href="https://example.com/">
  <meta property="og:title" content="SmartLaunch QA">
  <meta property="og:description" content="Pre-launch QA for websites">
  <meta property="og:image" content="https://example.com/og.png">
</head><body>
  <h1>SmartLaunch QA</h1>
  <img src="logo.png" alt="SmartLaunch QA logo">
</body></html>
"""


def test_good_page_yields_no_issues() -> None:
    assert audit_seo([_page(GOOD_PAGE)]) == []


def test_skips_pages_with_non_200_status() -> None:
    page = CrawledPage(
        url="https://x.test/", status_code=404, html=GOOD_PAGE, response_time_ms=10
    )
    assert audit_seo([page]) == []


def test_missing_title_is_critical() -> None:
    issues = audit_seo([_page("<html><head></head><body><h1>x</h1></body></html>")])
    titles = [i for i in issues if i.type == "missing_title"]
    assert titles
    assert titles[0].severity == Severity.critical


def test_short_title_is_warning() -> None:
    issues = audit_seo([_page("<html><head><title>short</title></head><body><h1>x</h1></body></html>")])
    assert "title_too_short" in _types(issues)


def test_long_title_is_warning() -> None:
    long_title = "x" * 100
    html = f"<html><head><title>{long_title}</title></head><body><h1>x</h1></body></html>"
    assert "title_too_long" in _types(audit_seo([_page(html)]))


def test_missing_meta_description_is_critical() -> None:
    html = "<html><head><title>" + "y" * 40 + "</title></head><body><h1>x</h1></body></html>"
    issues = audit_seo([_page(html)])
    desc = [i for i in issues if i.type == "missing_meta_description"]
    assert desc and desc[0].severity == Severity.critical


def test_missing_h1_is_critical() -> None:
    html = (
        "<html><head><title>"
        + "y" * 40
        + '</title><meta name="description" content="'
        + "z" * 80
        + '"></head><body><p>no heading</p></body></html>'
    )
    issues = audit_seo([_page(html)])
    h1 = [i for i in issues if i.type == "missing_h1"]
    assert h1 and h1[0].severity == Severity.critical


def test_multiple_h1_is_warning() -> None:
    html = (
        "<html><head><title>"
        + "y" * 40
        + '</title><meta name="description" content="'
        + "z" * 80
        + '"></head><body><h1>a</h1><h1>b</h1></body></html>'
    )
    assert "multiple_h1" in _types(audit_seo([_page(html)]))


def test_missing_canonical_is_warning() -> None:
    html = (
        "<html><head><title>"
        + "y" * 40
        + '</title><meta name="description" content="'
        + "z" * 80
        + '"></head><body><h1>x</h1></body></html>'
    )
    issues = audit_seo([_page(html)])
    canonical = [i for i in issues if i.type == "missing_canonical"]
    assert canonical and canonical[0].severity == Severity.warning


def test_missing_og_tags_each_reported() -> None:
    html = (
        "<html><head><title>"
        + "y" * 40
        + '</title><meta name="description" content="'
        + "z" * 80
        + '"><link rel="canonical" href="https://x.test/"></head><body><h1>x</h1></body></html>'
    )
    types = _types(audit_seo([_page(html)]))
    assert "missing_og_title" in types
    assert "missing_og_description" in types
    assert "missing_og_image" in types


def test_missing_alt_is_warning() -> None:
    html = (
        "<html><head><title>"
        + "y" * 40
        + '</title><meta name="description" content="'
        + "z" * 80
        + '"><link rel="canonical" href="https://x.test/"><meta property="og:title" content="x"><meta property="og:description" content="x"><meta property="og:image" content="https://x.test/x.png"></head>'
        '<body><h1>x</h1><img src="a.png"><img src="b.png" alt=""></body></html>'
    )
    issues = audit_seo([_page(html)])
    alt = [i for i in issues if i.type == "missing_alt_text"]
    assert alt and alt[0].severity == Severity.warning
    assert "2" in alt[0].message  # both <img> caught
