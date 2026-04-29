"use client";

import { useEffect, useState } from "react";

import { SeverityBadge } from "@/components/audits/severity-badge";
import { VerdictBadge } from "@/components/audits/verdict-badge";
import { ApiError } from "@/lib/api";
import { auditsApi, type DiffResponse } from "@/lib/audits";

export function DiffTab({ auditId }: { auditId: string }) {
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    auditsApi
      .diff(auditId)
      .then(setDiff)
      .catch((e) =>
        setError(e instanceof ApiError ? e.detail : "Failed to load diff"),
      );
  }, [auditId]);

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }
  if (!diff) {
    return <p className="text-sm text-muted-foreground">Loading diff…</p>;
  }
  if (!diff.pair_complete) {
    return (
      <p className="rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground">
        Diff isn’t ready yet — both staging and production audits need to complete first.
      </p>
    );
  }
  if (diff.diffs.length === 0) {
    return (
      <div className="space-y-3">
        <VerdictBadge verdict={diff.verdict} size="lg" />
        <p className="text-sm text-muted-foreground">
          No differences detected — staging and production are aligned.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <VerdictBadge verdict={diff.verdict} size="lg" />

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2 text-left">Page</th>
              <th className="px-4 py-2 text-left">Field</th>
              <th className="px-4 py-2 text-left">Severity</th>
              <th className="px-4 py-2 text-left">Staging</th>
              <th className="px-4 py-2 text-left">Production</th>
            </tr>
          </thead>
          <tbody>
            {diff.diffs.map((d) => (
              <tr key={d.id} className="border-t border-border align-top">
                <td className="px-4 py-2 font-mono text-xs">{d.page_url}</td>
                <td className="px-4 py-2">{d.field}</td>
                <td className="px-4 py-2">
                  <SeverityBadge severity={d.severity} />
                </td>
                <td className="max-w-xs px-4 py-2">
                  <ValueCell value={d.staging_value} />
                </td>
                <td className="max-w-xs px-4 py-2">
                  <ValueCell value={d.production_value} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ValueCell({ value }: { value: string | null }) {
  if (value === null) {
    return <span className="text-muted-foreground">—</span>;
  }
  return <span className="break-all text-sm">{value}</span>;
}
