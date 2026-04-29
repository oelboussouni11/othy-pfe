"""Compare two crawled snapshots (staging vs production) and emit Diff records.

Categories per BUILD.md §5:
- pages presence (missing/added)
- HTTP status regressions
- SEO tag changes (title, meta description, h1, canonical)
- Open Graph tag changes (og:title, og:description, og:image)

Verdict (No-Go) triggers:
- production page returns 4xx/5xx that worked in staging
- production is missing pages that exist in staging (and worked there)
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from audit_engine.types import CrawledPage, Severity


class ChangeType(StrEnum):
    added_in_production = "added_in_production"
    removed_in_production = "removed_in_production"
    modified = "modified"


class Verdict(StrEnum):
    go = "go"
    no_go = "no_go"


@dataclass(frozen=True)
class Diff:
    page_url: str  # normalized path
    field: str
    staging_value: str | None
    production_value: str | None
    change_type: ChangeType
    severity: Severity


SEO_FIELDS = ("title", "meta_description", "h1", "canonical")
OG_FIELDS = ("og:title", "og:description", "og:image")


# ---------- URL normalization ----------


def _path_key(url: str) -> str:
    """Strip scheme/host/port/fragment. Keep path + query. Normalize trailing slash."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path


# ---------- HTML extractors ----------


def _extract(soup: BeautifulSoup, field: str) -> str | None:
    if field == "title":
        tag = soup.find("title")
        return tag.text.strip() if tag and tag.text else None
    if field == "meta_description":
        tag = soup.find("meta", attrs={"name": "description"})
        return (tag.get("content") or "").strip() if tag else None
    if field == "h1":
        tag = soup.find("h1")
        return tag.text.strip() if tag and tag.text else None
    if field == "canonical":
        tag = soup.find("link", attrs={"rel": "canonical"})
        return (tag.get("href") or "").strip() if tag else None
    if field.startswith("og:"):
        tag = soup.find("meta", attrs={"property": field})
        return (tag.get("content") or "").strip() if tag else None
    raise ValueError(f"unknown field {field}")


# ---------- main ----------


def diff_environments(
    staging: Iterable[CrawledPage],
    production: Iterable[CrawledPage],
) -> list[Diff]:
    s_by_path = {_path_key(p.url): p for p in staging}
    p_by_path = {_path_key(p.url): p for p in production}

    diffs: list[Diff] = []
    diffs.extend(_diff_presence(s_by_path, p_by_path))

    for path in sorted(s_by_path.keys() & p_by_path.keys()):
        diffs.extend(_diff_pair(path, s_by_path[path], p_by_path[path]))

    return diffs


def _diff_presence(
    s_by_path: dict[str, CrawledPage], p_by_path: dict[str, CrawledPage]
) -> Iterator[Diff]:
    for path in sorted(s_by_path.keys() - p_by_path.keys()):
        staging_page = s_by_path[path]
        # Critical only when staging served the page successfully — if staging itself
        # 404s and production also doesn't have it, that's not a launch blocker.
        severity = Severity.critical if 200 <= staging_page.status_code < 300 else Severity.warning
        yield Diff(
            page_url=path,
            field="presence",
            staging_value=str(staging_page.status_code),
            production_value=None,
            change_type=ChangeType.removed_in_production,
            severity=severity,
        )

    for path in sorted(p_by_path.keys() - s_by_path.keys()):
        production_page = p_by_path[path]
        yield Diff(
            page_url=path,
            field="presence",
            staging_value=None,
            production_value=str(production_page.status_code),
            change_type=ChangeType.added_in_production,
            severity=Severity.info,
        )


def _diff_pair(path: str, staging: CrawledPage, prod: CrawledPage) -> Iterator[Diff]:
    # HTTP regression — most important signal
    s_ok = 200 <= staging.status_code < 300
    p_failed = prod.status_code >= 400 or prod.status_code == 0
    if s_ok and p_failed:
        yield Diff(
            page_url=path,
            field="status_code",
            staging_value=str(staging.status_code),
            production_value=str(prod.status_code),
            change_type=ChangeType.modified,
            severity=Severity.critical,
        )
    elif staging.status_code != prod.status_code:
        # Non-regression status drift — informational
        yield Diff(
            page_url=path,
            field="status_code",
            staging_value=str(staging.status_code),
            production_value=str(prod.status_code),
            change_type=ChangeType.modified,
            severity=Severity.info,
        )

    # HTML-derived fields — only meaningful if both responded with HTML
    if not staging.html or not prod.html:
        return

    s_soup = BeautifulSoup(staging.html, "lxml")
    p_soup = BeautifulSoup(prod.html, "lxml")

    for field in SEO_FIELDS:
        s_val = _extract(s_soup, field)
        p_val = _extract(p_soup, field)
        if s_val != p_val:
            yield Diff(
                page_url=path,
                field=field,
                staging_value=s_val,
                production_value=p_val,
                change_type=ChangeType.modified,
                severity=Severity.warning,
            )

    for field in OG_FIELDS:
        s_val = _extract(s_soup, field)
        p_val = _extract(p_soup, field)
        if s_val != p_val:
            # Going from set → unset is more notable than just changing copy
            severity = Severity.warning if (s_val and not p_val) else Severity.info
            yield Diff(
                page_url=path,
                field=field,
                staging_value=s_val,
                production_value=p_val,
                change_type=ChangeType.modified,
                severity=severity,
            )


# ---------- verdict ----------


def compute_verdict(diffs: Iterable[Diff]) -> tuple[Verdict, list[str]]:
    """Returns (verdict, human-readable reasons triggering No-Go)."""
    reasons: list[str] = []
    for d in diffs:
        if d.severity != Severity.critical:
            continue
        if d.field == "presence" and d.change_type == ChangeType.removed_in_production:
            reasons.append(
                f"{d.page_url}: served {d.staging_value} in staging, missing in production"
            )
        elif d.field == "status_code":
            reasons.append(
                f"{d.page_url}: {d.staging_value} in staging → {d.production_value} in production"
            )
        else:
            reasons.append(f"{d.page_url}: critical change in {d.field}")
    return (Verdict.no_go if reasons else Verdict.go), reasons
