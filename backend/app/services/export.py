"""Render an audit as a standalone HTML document. Inline CSS — no external deps."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import Audit


_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
       margin: 0; padding: 2rem; background: #fafafa; color: #18181b; }
.wrap { max-width: 980px; margin: 0 auto; }
header { margin-bottom: 1.5rem; }
h1 { margin: 0 0 .25rem; font-size: 1.75rem; }
.meta { color: #71717a; font-size: .875rem; }
.card { background: white; border: 1px solid #e4e4e7; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; }
.stat-label { font-size: .7rem; text-transform: uppercase; letter-spacing: .05em; color: #71717a; }
.stat-value { font-size: 1.5rem; font-weight: 600; margin-top: .25rem; font-variant-numeric: tabular-nums; }
.badge { display: inline-flex; align-items: center; gap: .25rem; padding: .25rem .6rem;
         border-radius: 999px; font-size: .75rem; font-weight: 500; }
.badge-go { background: #d1fae5; color: #065f46; }
.badge-no-go { background: #fee2e2; color: #991b1b; }
.badge-pending { background: #f4f4f5; color: #71717a; }
.sev { display: inline-block; padding: .15rem .5rem; border-radius: 999px; font-size: .7rem; font-weight: 500; }
.sev-critical { background: #fee2e2; color: #991b1b; }
.sev-warning { background: #fef3c7; color: #92400e; }
.sev-info { background: #dbeafe; color: #1e40af; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th { background: #f4f4f5; text-transform: uppercase; font-size: .7rem;
     letter-spacing: .05em; color: #71717a; text-align: left; padding: .5rem .75rem; }
td { padding: .6rem .75rem; border-top: 1px solid #e4e4e7; vertical-align: top; }
td.url { font-family: ui-monospace, SFMono-Regular, monospace; font-size: .8rem; word-break: break-all; }
.muted { color: #71717a; }
.error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: .75rem 1rem; border-radius: 6px; }
"""


def _verdict_badge(verdict: str | None, status: str) -> str:
    if status in ("queued", "running"):
        return '<span class="badge badge-pending">Pending</span>'
    if verdict == "go":
        return '<span class="badge badge-go">Go</span>'
    if verdict == "no_go":
        return '<span class="badge badge-no-go">No-Go</span>'
    return '<span class="badge badge-pending">—</span>'


def _stat(label: str, value: str | int) -> str:
    return f"""<div>
        <div class="stat-label">{escape(label)}</div>
        <div class="stat-value">{escape(str(value))}</div>
    </div>"""


def render_audit(audit: Audit) -> str:
    project = audit.project
    score = "—" if audit.seo_score is None else str(audit.seo_score)
    title_text = f"{project.name} · audit {audit.id[:8]}"

    issues_rows = (
        "".join(
            f"""<tr>
            <td><span class="sev sev-{escape(i.severity.value)}">{escape(i.severity.value)}</span></td>
            <td>{escape(i.type)}</td>
            <td>{escape(i.message)}</td>
            <td class="url">{escape(i.page_url)}</td>
        </tr>"""
            for i in audit.issues
        )
        or '<tr><td colspan="4" class="muted">No issues recorded.</td></tr>'
    )

    diffs_section = ""
    if audit.diffs:
        diff_rows = "".join(
            f"""<tr>
                <td class="url">{escape(d.page_url)}</td>
                <td>{escape(d.field)}</td>
                <td><span class="sev sev-{escape(d.severity.value)}">{escape(d.severity.value)}</span></td>
                <td>{escape(d.staging_value or "—")}</td>
                <td>{escape(d.production_value or "—")}</td>
            </tr>"""
            for d in audit.diffs
        )
        diffs_section = f"""<section class="card">
            <h2 style="margin:0 0 .75rem; font-size: 1.1rem;">Diff (staging vs production)</h2>
            <table>
                <thead><tr>
                    <th>Page</th><th>Field</th><th>Severity</th><th>Staging</th><th>Production</th>
                </tr></thead>
                <tbody>{diff_rows}</tbody>
            </table>
        </section>"""

    error_block = (
        f'<div class="error">{escape(audit.error_message)}</div>' if audit.error_message else ""
    )

    return f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title_text)}</title>
  <style>{_CSS}</style>
</head><body><div class="wrap">
  <header>
    <h1>{escape(project.name)}</h1>
    <div class="meta">
      Audit · {escape(audit.environment.value)} ·
      {escape(audit.created_at.isoformat())} · {escape(audit.status.value)}
    </div>
  </header>

  <section class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;gap:.5rem;flex-wrap:wrap;">
      <div>{_verdict_badge(audit.verdict.value if audit.verdict else None, audit.status.value)}</div>
      <a class="muted" style="text-decoration:none;font-size:.8rem;" href="{escape(project.production_url)}" target="_blank">{escape(project.production_url)}</a>
    </div>
    {error_block}
    <div class="stats">
      {_stat("Pages crawled", audit.pages_crawled)}
      {_stat("Broken links", audit.broken_links_count)}
      {_stat("SEO score", score)}
      {_stat("Issues", len(audit.issues))}
    </div>
  </section>

  {diffs_section}

  <section class="card">
    <h2 style="margin:0 0 .75rem; font-size: 1.1rem;">Issues ({len(audit.issues)})</h2>
    <table>
        <thead><tr>
            <th>Severity</th><th>Type</th><th>Message</th><th>Page</th>
        </tr></thead>
        <tbody>{issues_rows}</tbody>
    </table>
  </section>

  <p class="meta" style="text-align:center; margin-top: 2rem;">
    Generated by SmartLaunch QA
  </p>
</div></body></html>"""
