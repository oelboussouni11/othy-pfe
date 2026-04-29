"""Async crawler. Polite by default: respects robots.txt, caps concurrency, retries once."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from audit_engine.types import CrawledPage

USER_AGENT = "SmartLaunchQA/1.0"
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawlConfig:
    max_pages: int = 100
    max_concurrency: int = 5
    timeout_seconds: float = 10.0
    same_origin_only: bool = True
    user_agent: str = USER_AGENT
    respect_robots: bool = True


def _normalize(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urlparse(a), urlparse(b)
    return pa.scheme == pb.scheme and pa.netloc == pb.netloc


def _is_html(content_type: str | None) -> bool:
    return "text/html" in (content_type or "").lower()


def _is_sitemap_url(url: str) -> bool:
    lowered = url.lower()
    return lowered.endswith(".xml") or "sitemap" in lowered


def _extract_links(base_url: str, html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        links.add(_normalize(urljoin(base_url, href)))
    return links


async def _load_robots(client: httpx.AsyncClient, origin: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(f"{origin}/robots.txt")
    try:
        res = await client.get(f"{origin}/robots.txt", timeout=5.0)
        if res.status_code == 200:
            rp.parse(res.text.splitlines())
    except httpx.RequestError:
        log.debug("robots.txt fetch failed for %s; allowing all", origin)
    return rp


async def _fetch_with_retry(
    client: httpx.AsyncClient, url: str, timeout: float
) -> tuple[httpx.Response | None, Exception | None]:
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            res = await client.get(url, timeout=timeout, follow_redirects=True)
            return res, None
        except httpx.RequestError as e:
            last_err = e
            log.debug("fetch error for %s (attempt %d): %s", url, attempt + 1, e)
    return None, last_err


async def _parse_sitemap(client: httpx.AsyncClient, url: str) -> list[str]:
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code != 200:
            return []
    except httpx.RequestError:
        return []
    soup = BeautifulSoup(res.text, "xml")
    return [loc.text.strip() for loc in soup.find_all("loc") if loc.text]


async def crawl(seed_url: str, config: CrawlConfig | None = None) -> list[CrawledPage]:
    cfg = config or CrawlConfig()
    parsed_seed = urlparse(seed_url)
    origin = f"{parsed_seed.scheme}://{parsed_seed.netloc}"
    semaphore = asyncio.Semaphore(cfg.max_concurrency)

    async with httpx.AsyncClient(headers={"User-Agent": cfg.user_agent}) as client:
        rp = await _load_robots(client, origin) if cfg.respect_robots else None

        # Discover seed URLs (sitemap or single page)
        if _is_sitemap_url(seed_url):
            seeds = await _parse_sitemap(client, seed_url) or [seed_url]
        else:
            seeds = [seed_url]

        seen: set[str] = set()
        queue: list[str] = []
        for s in seeds:
            n = _normalize(s)
            if n not in seen:
                seen.add(n)
                queue.append(n)

        results: list[CrawledPage] = []

        async def fetch_one(url: str) -> CrawledPage | None:
            if rp is not None and not rp.can_fetch(cfg.user_agent, url):
                log.debug("robots.txt disallows %s", url)
                return None
            async with semaphore:
                start = time.monotonic()
                res, err = await _fetch_with_retry(client, url, cfg.timeout_seconds)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if err is not None or res is None:
                    return CrawledPage(url=url, status_code=0, html="", response_time_ms=elapsed_ms)

                html = res.text if _is_html(res.headers.get("content-type")) else ""
                return CrawledPage(
                    url=str(res.url),
                    status_code=res.status_code,
                    html=html,
                    response_time_ms=elapsed_ms,
                )

        # BFS
        while queue and len(results) < cfg.max_pages:
            batch = queue[: cfg.max_concurrency]
            queue = queue[cfg.max_concurrency :]
            crawled = await asyncio.gather(*(fetch_one(u) for u in batch))

            for page in crawled:
                if page is None:
                    continue
                if len(results) >= cfg.max_pages:
                    break
                results.append(page)
                if not page.html:
                    continue

                for link in _extract_links(page.url, page.html):
                    if link in seen:
                        continue
                    if cfg.same_origin_only and not _same_origin(seed_url, link):
                        continue
                    seen.add(link)
                    queue.append(link)

        return results
