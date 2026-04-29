"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { SeverityBadge } from "@/components/audits/severity-badge";
import { summarizeIssues, type Insight } from "@/lib/audit-insights";
import type { AuditIssue } from "@/lib/audits";
import { cn } from "@/lib/utils";

const PREVIEW_LIMIT = 6;

export function InsightsPanel({ issues }: { issues: AuditIssue[] }) {
  const insights = summarizeIssues(issues);
  const [expanded, setExpanded] = useState(false);

  if (insights.length === 0) {
    return (
      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-sm font-medium">What we found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          No issues found across this audit. Either the site is squeaky clean or the audit
          hasn’t finished crawling yet.
        </p>
      </section>
    );
  }

  const preview = expanded ? insights : insights.slice(0, PREVIEW_LIMIT);
  const hidden = insights.length - preview.length;

  const counts = {
    critical: insights.filter((i) => i.severity === "critical").reduce((s, i) => s + i.count, 0),
    warning: insights.filter((i) => i.severity === "warning").reduce((s, i) => s + i.count, 0),
    info: insights.filter((i) => i.severity === "info").reduce((s, i) => s + i.count, 0),
  };

  return (
    <section className="space-y-4 rounded-lg border border-border bg-card p-5">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium">What we found</h2>
        <div className="flex flex-wrap gap-2 text-xs">
          {counts.critical > 0 && (
            <span className="rounded-full bg-destructive/15 px-2 py-0.5 font-medium text-destructive">
              {counts.critical} critical
            </span>
          )}
          {counts.warning > 0 && (
            <span className="rounded-full bg-amber-500/15 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-400">
              {counts.warning} warning
            </span>
          )}
          {counts.info > 0 && (
            <span className="rounded-full bg-blue-500/15 px-2 py-0.5 font-medium text-blue-700 dark:text-blue-400">
              {counts.info} info
            </span>
          )}
        </div>
      </header>

      <ul className="space-y-3">
        {preview.map((insight) => (
          <InsightCard key={insight.type} insight={insight} />
        ))}
      </ul>

      {hidden > 0 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          Show {hidden} more <ChevronDown className="h-4 w-4" />
        </button>
      )}
    </section>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const accent =
    insight.severity === "critical"
      ? "border-l-destructive"
      : insight.severity === "warning"
        ? "border-l-amber-500"
        : "border-l-blue-500";

  return (
    <li className={cn("rounded-md border border-border border-l-4 bg-background p-4", accent)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={insight.severity} />
            <span className="text-sm font-medium">{insight.label}</span>
          </div>
          {insight.why && (
            <p className="text-sm text-muted-foreground">{insight.why}</p>
          )}
        </div>
        <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium tabular-nums">
          {insight.count} {insight.count === 1 ? "page" : "pages"}
        </span>
      </div>

      {insight.recommendation && (
        <p className="mt-3 rounded-md bg-muted/50 p-2 text-sm">
          <span className="font-medium">Fix:</span> {insight.recommendation}
        </p>
      )}

      {insight.example_pages.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
            Example pages ({insight.example_pages.length})
          </summary>
          <ul className="mt-1 space-y-0.5 pl-4">
            {insight.example_pages.map((url) => (
              <li key={url} className="font-mono text-xs text-muted-foreground break-all">
                {url}
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}
