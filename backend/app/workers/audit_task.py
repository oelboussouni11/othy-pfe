"""RQ task: run an audit end-to-end and persist results.

Designed to be callable from tests too — pass a session_factory to override the default.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from audit_engine.checks.links import audit_links
from audit_engine.checks.seo import audit_seo
from audit_engine.crawler import crawl
from audit_engine.types import CrawledPage, Issue
from sqlalchemy.orm import Session

from app.db.models import (
    Audit,
    AuditEnvironment,
    AuditIssue,
    AuditStatus,
    IssueSeverity,
)
from app.db.session import SessionLocal

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _seo_score(issues: Iterable[Issue]) -> int:
    """Simple penalty-based score in [0, 100]: -10 per critical, -3 per warning, -1 per info."""
    weights = {"critical": 10, "warning": 3, "info": 1}
    penalty = sum(weights.get(i.severity.value, 0) for i in issues)
    return max(0, min(100, 100 - penalty))


def _broken_links_count(issues: Iterable[Issue]) -> int:
    """Critical-severity link issues — what a PM would call 'broken'."""
    bad_types = {"broken_link", "client_error", "server_error"}
    return sum(1 for i in issues if i.type in bad_types)


def _resolve_target_url(audit: Audit) -> str | None:
    project = audit.project
    if audit.environment == AuditEnvironment.production:
        return project.production_url
    return project.staging_url


def _persist_issues(db: Session, audit_id: str, issues: Iterable[Issue]) -> None:
    for issue in issues:
        db.add(
            AuditIssue(
                audit_id=audit_id,
                page_url=issue.page_url,
                type=issue.type,
                severity=IssueSeverity(issue.severity.value),
                message=issue.message,
                recommendation=issue.recommendation,
                status_code=issue.status_code,
            )
        )


async def _run_engine(target_url: str) -> tuple[list[CrawledPage], list[Issue], list[Issue]]:
    pages = await crawl(target_url)
    seo_issues = audit_seo(pages)
    link_issues = await audit_links(pages)
    return pages, seo_issues, link_issues


def run_audit(
    audit_id: str,
    *,
    session_factory: Callable[[], Session] | None = None,
) -> None:
    """Execute the audit identified by audit_id. Updates status + persists issues."""
    factory = session_factory or SessionLocal
    db = factory()
    try:
        audit = db.get(Audit, audit_id)
        if audit is None:
            log.warning("audit %s not found; skipping", audit_id)
            return

        target_url = _resolve_target_url(audit)
        if not target_url:
            audit.status = AuditStatus.failed
            audit.error_message = f"no {audit.environment.value}_url configured on project"
            audit.finished_at = _now()
            db.commit()
            return

        audit.status = AuditStatus.running
        audit.started_at = _now()
        db.commit()

        try:
            pages, seo_issues, link_issues = asyncio.run(_run_engine(target_url))
        except Exception as e:  # noqa: BLE001 — worker top-level catch
            log.exception("audit %s failed during engine run", audit_id)
            audit.status = AuditStatus.failed
            audit.error_message = f"{type(e).__name__}: {e}"
            audit.finished_at = _now()
            db.commit()
            raise

        all_issues = list(seo_issues) + list(link_issues)
        _persist_issues(db, audit.id, all_issues)

        audit.pages_crawled = len(pages)
        audit.broken_links_count = _broken_links_count(link_issues)
        audit.seo_score = _seo_score(seo_issues)
        audit.status = AuditStatus.completed
        audit.finished_at = _now()
        db.commit()

        _maybe_run_diff(db, audit)
    finally:
        db.close()


def _maybe_run_diff(db: Session, audit: Audit) -> None:
    """If both halves of a paired run are completed, trigger the diff pass.

    Either side completing last lands here. We always run diff against the production
    audit (the diff "owner") regardless of which side called us in.
    """
    # Local import: services/diff.py imports models too, this avoids cycles at import time.
    from app.services.diff import both_audits_completed, run_diff_for_pair

    companion = audit.companion
    if not both_audits_completed(audit, companion):
        return

    production_id = audit.id if audit.environment == AuditEnvironment.production else companion.id
    run_diff_for_pair(db, production_id)
