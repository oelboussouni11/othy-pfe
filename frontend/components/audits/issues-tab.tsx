"use client";

import { useMemo, useState } from "react";

import { SeverityBadge } from "@/components/audits/severity-badge";
import type { AuditIssue, Severity } from "@/lib/audits";

const SEVERITIES: Severity[] = ["critical", "warning", "info"];

export function IssuesTab({ issues }: { issues: AuditIssue[] }) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const types = useMemo(() => {
    const set = new Set(issues.map((i) => i.type));
    return ["all", ...Array.from(set).sort()];
  }, [issues]);

  const filtered = useMemo(
    () =>
      issues.filter(
        (i) =>
          (severityFilter === "all" || i.severity === severityFilter) &&
          (typeFilter === "all" || i.type === typeFilter),
      ),
    [issues, severityFilter, typeFilter],
  );

  if (issues.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground">
        No issues found.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-sm">
        <Select label="Severity" value={severityFilter} onChange={(v) => setSeverityFilter(v as Severity | "all")}>
          <option value="all">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <Select label="Type" value={typeFilter} onChange={setTypeFilter}>
          {types.map((t) => (
            <option key={t} value={t}>
              {t === "all" ? "All types" : t}
            </option>
          ))}
        </Select>
        <span className="ml-auto self-center text-xs text-muted-foreground">
          {filtered.length} of {issues.length}
        </span>
      </div>

      <ul className="space-y-2">
        {filtered.map((issue) => (
          <li key={issue.id} className="rounded-lg border border-border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={issue.severity} />
                  <span className="text-xs font-mono text-muted-foreground">{issue.type}</span>
                </div>
                <p className="text-sm">{issue.message}</p>
                <p className="text-xs text-muted-foreground">{issue.page_url}</p>
              </div>
              {issue.status_code != null && (
                <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-mono">
                  {issue.status_code}
                </span>
              )}
            </div>
            {issue.recommendation && (
              <p className="mt-2 text-xs text-muted-foreground">→ {issue.recommendation}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-center gap-2">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-input bg-background px-2 py-1 text-sm"
      >
        {children}
      </select>
    </label>
  );
}
