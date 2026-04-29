"""Diff engine tests — pure HTML, no network. Covers BUILD.md §5 verdict scenarios."""

from audit_engine.checks.diff import (
    ChangeType,
    Verdict,
    _path_key,
    compute_verdict,
    diff_environments,
)
from audit_engine.types import CrawledPage, Severity


def _ok(url: str, html: str = "") -> CrawledPage:
    return CrawledPage(url=url, status_code=200, html=html, response_time_ms=10)


def _status(url: str, code: int) -> CrawledPage:
    return CrawledPage(url=url, status_code=code, html="", response_time_ms=10)


def _by_field(diffs):
    return {(d.page_url, d.field): d for d in diffs}


# ---------- URL normalization ----------


def test_path_key_strips_origin_and_normalizes_slash() -> None:
    assert _path_key("https://acme.com/about/") == "/about"
    assert _path_key("https://staging.acme.com/about") == "/about"
    assert _path_key("https://acme.com/") == "/"


def test_path_key_keeps_query() -> None:
    assert _path_key("https://acme.com/search?q=x") == "/search?q=x"


# ---------- presence ----------


def test_page_missing_in_production_is_critical() -> None:
    """Scenario from BUILD.md §16: staging has 10 pages, production has 9 → No-Go."""
    staging = [_ok("https://staging.x/"), _ok("https://staging.x/about")]
    production = [_ok("https://x.com/")]

    diffs = diff_environments(staging, production)
    by = _by_field(diffs)
    missing = by[("/about", "presence")]
    assert missing.change_type == ChangeType.removed_in_production
    assert missing.severity == Severity.critical


def test_page_added_in_production_is_info() -> None:
    staging = [_ok("https://staging.x/")]
    production = [_ok("https://x.com/"), _ok("https://x.com/new")]

    diffs = diff_environments(staging, production)
    added = _by_field(diffs)[("/new", "presence")]
    assert added.change_type == ChangeType.added_in_production
    assert added.severity == Severity.info


def test_missing_page_that_already_404d_in_staging_is_only_warning() -> None:
    staging = [_ok("https://staging.x/"), _status("https://staging.x/draft", 404)]
    production = [_ok("https://x.com/")]
    missing = _by_field(diff_environments(staging, production))[("/draft", "presence")]
    assert missing.severity == Severity.warning


# ---------- HTTP regression ----------


def test_http_200_to_500_is_critical() -> None:
    """Scenario from BUILD.md §16: link worked in staging, 404 in prod → No-Go."""
    staging = [_ok("https://staging.x/api")]
    production = [_status("https://x.com/api", 500)]

    diffs = diff_environments(staging, production)
    diff = _by_field(diffs)[("/api", "status_code")]
    assert diff.severity == Severity.critical
    assert diff.staging_value == "200"
    assert diff.production_value == "500"


def test_status_drift_without_regression_is_info() -> None:
    """Both 200 → no diff. 200 in staging, 301 in production → info (it's a redirect, not broken)."""
    staging = [_ok("https://staging.x/old")]
    production = [_status("https://x.com/old", 301)]

    diffs = diff_environments(staging, production)
    # 301 is technically not 4xx/5xx so it shouldn't be critical
    diff = _by_field(diffs)[("/old", "status_code")]
    assert diff.severity == Severity.info


# ---------- SEO tags ----------


def test_title_changed_is_warning() -> None:
    """Scenario from BUILD.md §16: title changed between envs → flagged warning, still Go."""
    s_html = "<html><head><title>Old Title</title></head><body></body></html>"
    p_html = "<html><head><title>New Title</title></head><body></body></html>"
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    diff = _by_field(diffs)[("/", "title")]
    assert diff.severity == Severity.warning
    assert diff.staging_value == "Old Title"
    assert diff.production_value == "New Title"


def test_h1_changed_is_warning() -> None:
    s_html = "<html><body><h1>Hello</h1></body></html>"
    p_html = "<html><body><h1>Hi</h1></body></html>"
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    h1 = _by_field(diffs)[("/", "h1")]
    assert h1.severity == Severity.warning


def test_meta_description_change_detected() -> None:
    s_html = '<html><head><meta name="description" content="Old"></head></html>'
    p_html = '<html><head><meta name="description" content="New"></head></html>'
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    assert ("/", "meta_description") in _by_field(diffs)


# ---------- Open Graph ----------


def test_og_image_removed_is_warning() -> None:
    s_html = '<html><head><meta property="og:image" content="https://s.x/og.png"></head></html>'
    p_html = "<html><head></head></html>"
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    og = _by_field(diffs)[("/", "og:image")]
    assert og.severity == Severity.warning  # set→unset
    assert og.staging_value == "https://s.x/og.png"
    assert og.production_value is None


def test_og_image_changed_is_info() -> None:
    s_html = '<html><head><meta property="og:image" content="https://s.x/a.png"></head></html>'
    p_html = '<html><head><meta property="og:image" content="https://p.x/b.png"></head></html>'
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    og = _by_field(diffs)[("/", "og:image")]
    assert og.severity == Severity.info  # different copy, not removal


# ---------- verdict ----------


def test_verdict_go_when_no_critical_issues() -> None:
    """BUILD.md §16: title changed → still Go (warnings allowed)."""
    s_html = "<html><head><title>A</title></head></html>"
    p_html = "<html><head><title>B</title></head></html>"
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, s_html, 10)],
        [CrawledPage("https://p.x/", 200, p_html, 10)],
    )
    verdict, reasons = compute_verdict(diffs)
    assert verdict == Verdict.go
    assert reasons == []


def test_verdict_no_go_when_production_404s_a_page_that_worked_in_staging() -> None:
    diffs = diff_environments(
        [_ok("https://s.x/api")],
        [_status("https://p.x/api", 404)],
    )
    verdict, reasons = compute_verdict(diffs)
    assert verdict == Verdict.no_go
    assert any("/api" in r and "404" in r for r in reasons)


def test_verdict_no_go_when_production_missing_pages() -> None:
    diffs = diff_environments(
        [_ok("https://s.x/"), _ok("https://s.x/about")],
        [_ok("https://p.x/")],
    )
    verdict, reasons = compute_verdict(diffs)
    assert verdict == Verdict.no_go
    assert any("/about" in r for r in reasons)


def test_verdict_reasons_are_human_readable() -> None:
    """BUILD.md §16: 'Verdict reasoning is human-readable (list of triggering issues)'."""
    diffs = diff_environments(
        [_ok("https://s.x/api"), _ok("https://s.x/products")],
        [_status("https://p.x/api", 500), _ok("https://p.x/products")],
    )
    _, reasons = compute_verdict(diffs)
    assert reasons
    # Each reason should mention a path and what changed
    assert all("/" in r for r in reasons)


def test_diff_with_no_changes_yields_empty_and_go() -> None:
    same = "<html><head><title>x</title></head><body><h1>x</h1></body></html>"
    diffs = diff_environments(
        [CrawledPage("https://s.x/", 200, same, 10)],
        [CrawledPage("https://p.x/", 200, same, 10)],
    )
    assert diffs == []
    verdict, reasons = compute_verdict(diffs)
    assert verdict == Verdict.go
    assert reasons == []
