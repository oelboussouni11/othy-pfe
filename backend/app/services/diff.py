"""Diff orchestration: collect crawled snapshots from a paired audit and persist results."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx
from audit_engine.checks.diff import ChangeType as EngineChangeType
from audit_engine.checks.diff import (
    Verdict as EngineVerdict,
)
from audit_engine.checks.diff import (
    compute_verdict,
    diff_environments,
)
from audit_engine.crawler import crawl
from audit_engine.types import CrawledPage
from sqlalchemy.orm import Session

from app.db.models import (
    Audit,
    AuditDiff,
    AuditEnvironment,
    AuditStatus,
    DiffChangeType,
    IssueSeverity,
    Verdict,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiffResult:
    diffs: list  # list[Diff] from audit_engine
    verdict: EngineVerdict
    reasons: list[str]


def both_audits_completed(audit_a: Audit, audit_b: Audit | None) -> bool:
    return (
        audit_b is not None
        and audit_a.status == AuditStatus.completed
        and audit_b.status == AuditStatus.completed
    )


def _split_pair(audit_a: Audit, audit_b: Audit) -> tuple[Audit, Audit]:
    """Returns (production_audit, staging_audit) for a paired run."""
    if audit_a.environment == AuditEnvironment.production:
        return audit_a, audit_b
    return audit_b, audit_a


def _engine_to_db_change_type(t: EngineChangeType) -> DiffChangeType:
    return DiffChangeType(t.value)


async def _crawl_both(
    staging_url: str, production_url: str
) -> tuple[list[CrawledPage], list[CrawledPage]]:
    """Re-crawl both environments in parallel for the diff pass."""
    return await asyncio.gather(crawl(staging_url), crawl(production_url))


def run_diff_for_pair(db: Session, audit_id: str) -> DiffResult | None:
    """Compute and persist the diff for the production audit identified by audit_id.

    Returns None if the pair isn't ready (companion missing or not completed) or if this
    audit isn't the production half. Idempotent — re-running clears prior diff rows.
    """
    audit = db.get(Audit, audit_id)
    if audit is None:
        log.warning("diff: audit %s not found", audit_id)
        return None

    if audit.environment != AuditEnvironment.production:
        # Only the production audit owns the diff rows. Staging side is a no-op here.
        return None

    companion = audit.companion
    if not both_audits_completed(audit, companion):
        return None

    project = audit.project
    if not project.staging_url or not project.production_url:
        log.warning("diff: project %s missing one of the URLs", project.id)
        return None

    # Re-crawl. We could persist HTML on the original audits to skip this, but
    # that triples DB volume; re-crawling for the diff pass keeps things simple.
    try:
        staging_pages, production_pages = asyncio.run(
            _crawl_both(project.staging_url, project.production_url)
        )
    except (httpx.RequestError, RuntimeError) as e:
        log.exception("diff: crawl failed for audit %s", audit_id)
        audit.error_message = f"diff crawl failed: {type(e).__name__}: {e}"
        db.commit()
        return None

    diffs = diff_environments(staging_pages, production_pages)
    verdict, reasons = compute_verdict(diffs)

    # Replace any prior diff rows for this audit (idempotent).
    db.query(AuditDiff).filter_by(audit_id=audit.id).delete()
    for d in diffs:
        db.add(
            AuditDiff(
                audit_id=audit.id,
                page_url=d.page_url,
                field=d.field,
                staging_value=d.staging_value,
                production_value=d.production_value,
                change_type=_engine_to_db_change_type(d.change_type),
                severity=IssueSeverity(d.severity.value),
            )
        )

    audit.verdict = Verdict(verdict.value)
    db.commit()

    return DiffResult(diffs=diffs, verdict=verdict, reasons=reasons)
