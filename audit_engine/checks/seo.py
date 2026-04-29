"""Per-page SEO checks: title, meta description, h1, canonical, Open Graph, alt text."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from bs4 import BeautifulSoup

from audit_engine.types import CrawledPage, Issue, Severity

TITLE_MIN, TITLE_MAX = 30, 65
META_DESC_MIN, META_DESC_MAX = 70, 160
OG_TAGS = ("og:title", "og:description", "og:image")


def audit_seo(pages: Iterable[CrawledPage]) -> list[Issue]:
    issues: list[Issue] = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "lxml")
        issues.extend(_check_title(page, soup))
        issues.extend(_check_meta_description(page, soup))
        issues.extend(_check_h1(page, soup))
        issues.extend(_check_canonical(page, soup))
        issues.extend(_check_og(page, soup))
        issues.extend(_check_alt_text(page, soup))
    return issues


# ---------- title ----------


def _check_title(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else ""
    if not title:
        yield Issue(
            page_url=page.url,
            type="missing_title",
            severity=Severity.critical,
            message="<title> is empty or missing",
            recommendation=f"Add a descriptive <title> ({TITLE_MIN}–{TITLE_MAX} chars).",
        )
        return
    if len(title) < TITLE_MIN:
        yield Issue(
            page_url=page.url,
            type="title_too_short",
            severity=Severity.warning,
            message=f"<title> is {len(title)} chars (min {TITLE_MIN})",
            recommendation=f"Expand the title to at least {TITLE_MIN} characters.",
        )
    elif len(title) > TITLE_MAX:
        yield Issue(
            page_url=page.url,
            type="title_too_long",
            severity=Severity.warning,
            message=f"<title> is {len(title)} chars (max {TITLE_MAX})",
            recommendation=f"Shorten the title to at most {TITLE_MAX} characters.",
        )


# ---------- meta description ----------


def _check_meta_description(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    tag = soup.find("meta", attrs={"name": "description"})
    content = (tag.get("content") or "").strip() if tag else ""
    if not content:
        yield Issue(
            page_url=page.url,
            type="missing_meta_description",
            severity=Severity.critical,
            message='<meta name="description"> is missing or empty',
            recommendation=f"Add a meta description ({META_DESC_MIN}–{META_DESC_MAX} chars).",
        )
        return
    if len(content) < META_DESC_MIN:
        yield Issue(
            page_url=page.url,
            type="meta_description_too_short",
            severity=Severity.warning,
            message=f"meta description is {len(content)} chars (min {META_DESC_MIN})",
            recommendation=f"Expand to at least {META_DESC_MIN} characters.",
        )
    elif len(content) > META_DESC_MAX:
        yield Issue(
            page_url=page.url,
            type="meta_description_too_long",
            severity=Severity.warning,
            message=f"meta description is {len(content)} chars (max {META_DESC_MAX})",
            recommendation=f"Shorten to at most {META_DESC_MAX} characters.",
        )


# ---------- h1 ----------


def _check_h1(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        yield Issue(
            page_url=page.url,
            type="missing_h1",
            severity=Severity.critical,
            message="page has no <h1>",
            recommendation="Add exactly one <h1> describing the page topic.",
        )
    elif len(h1s) > 1:
        yield Issue(
            page_url=page.url,
            type="multiple_h1",
            severity=Severity.warning,
            message=f"page has {len(h1s)} <h1> tags (expected 1)",
            recommendation="Keep one <h1>; demote the others to <h2> or below.",
        )


# ---------- canonical ----------


def _check_canonical(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    if not soup.find("link", attrs={"rel": "canonical"}):
        yield Issue(
            page_url=page.url,
            type="missing_canonical",
            severity=Severity.warning,
            message='<link rel="canonical"> is missing',
            recommendation="Add a canonical link pointing at this page's preferred URL.",
        )


# ---------- Open Graph ----------


def _check_og(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    for tag_name in OG_TAGS:
        tag = soup.find("meta", attrs={"property": tag_name})
        content = (tag.get("content") or "").strip() if tag else ""
        if not content:
            yield Issue(
                page_url=page.url,
                type=f"missing_{tag_name.replace(':', '_')}",
                severity=Severity.warning,
                message=f"{tag_name} is missing or empty",
                recommendation=f"Add <meta property=\"{tag_name}\" content=\"...\"> for social previews.",
            )


# ---------- alt text ----------


def _check_alt_text(page: CrawledPage, soup: BeautifulSoup) -> Iterator[Issue]:
    missing = 0
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if not alt:
            missing += 1
    if missing:
        yield Issue(
            page_url=page.url,
            type="missing_alt_text",
            severity=Severity.warning,
            message=f"{missing} <img> tag(s) without non-empty alt",
            recommendation="Add a descriptive alt for every image (or alt=\"\" for purely decorative).",
        )
