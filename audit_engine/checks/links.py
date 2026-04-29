"""Probe every <a href> in crawled pages and classify the response status."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from audit_engine.crawler import USER_AGENT
from audit_engine.types import CrawledPage, Issue, Severity

log = logging.getLogger(__name__)

REDIRECT_CHAIN_WARN_AT = 2  # > 2 hops triggers a warning


def _normalize(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def _extract_anchors(page_url: str, html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    out: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        out.add(_normalize(urljoin(page_url, href)))
    return out


def _classify(
    final_status: int, chain_length: int, first_redirect_status: int
) -> tuple[Severity, str, str]:
    """Returns (severity, type, message). final_status=0 indicates a network failure."""
    if final_status == 0:
        return Severity.critical, "broken_link", "request failed (network or timeout)"

    if chain_length > REDIRECT_CHAIN_WARN_AT:
        return Severity.warning, "long_redirect_chain", f"{chain_length} redirect hops"

    if chain_length > 0:
        if first_redirect_status in (301, 308):
            return Severity.info, "permanent_redirect", f"redirected via {first_redirect_status}"
        if first_redirect_status in (302, 303, 307):
            return (
                Severity.warning,
                "temporary_redirect",
                f"redirected via {first_redirect_status}",
            )

    if 200 <= final_status < 300:
        return Severity.ok, "ok_link", f"status {final_status}"
    if 400 <= final_status < 500:
        return Severity.critical, "client_error", f"status {final_status}"
    if final_status >= 500:
        return Severity.critical, "server_error", f"status {final_status}"
    return Severity.info, "unknown_status", f"status {final_status}"


async def _probe(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    timeout: float,
) -> tuple[int, int, int]:
    """Returns (final_status, chain_length, first_redirect_status). 0,0,0 on network failure."""
    async with semaphore:
        try:
            res = await client.get(url, timeout=timeout, follow_redirects=True)
            first_redirect = res.history[0].status_code if res.history else 0
            return res.status_code, len(res.history), first_redirect
        except httpx.RequestError as e:
            log.debug("probe failed for %s: %s", url, e)
            return 0, 0, 0


async def audit_links(
    pages: Iterable[CrawledPage],
    *,
    max_concurrency: int = 5,
    timeout: float = 10.0,
    user_agent: str = USER_AGENT,
) -> list[Issue]:
    """For every anchor in every page, check the link's status and report issues."""
    # Map link → list of pages that reference it
    link_to_pages: dict[str, list[str]] = {}
    for page in pages:
        if not page.html:
            continue
        for link in _extract_anchors(page.url, page.html):
            link_to_pages.setdefault(link, []).append(page.url)

    if not link_to_pages:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}) as client:
        unique = list(link_to_pages.keys())
        results = await asyncio.gather(*(_probe(client, url, semaphore, timeout) for url in unique))

    issues: list[Issue] = []
    for link, (final_status, chain_len, first_redirect) in zip(unique, results, strict=True):
        severity, issue_type, message = _classify(final_status, chain_len, first_redirect)
        if severity == Severity.ok:
            continue
        for page_url in link_to_pages[link]:
            issues.append(
                Issue(
                    page_url=page_url,
                    type=issue_type,
                    severity=severity,
                    message=f"{link}: {message}",
                    recommendation=_recommendation_for(issue_type),
                    status_code=final_status if final_status > 0 else None,
                )
            )
    return issues


def _recommendation_for(issue_type: str) -> str:
    return {
        "broken_link": "Verify the URL exists or remove the link.",
        "client_error": "Update or remove the link — it returned 4xx.",
        "server_error": "The destination server is failing. Retry or remove the link.",
        "temporary_redirect": "Replace with the final URL or convert to a 301 if permanent.",
        "permanent_redirect": "Update the link to the final destination to avoid the hop.",
        "long_redirect_chain": "Collapse the redirect chain — point directly to the final URL.",
    }.get(issue_type, "")
