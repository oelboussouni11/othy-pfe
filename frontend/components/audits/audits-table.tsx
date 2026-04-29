"use client";

import { Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AuditStatusBadge } from "@/components/audits/audit-status-badge";
import { VerdictBadge } from "@/components/audits/verdict-badge";
import { ApiError } from "@/lib/api";
import { auditsApi, type Audit } from "@/lib/audits";

export function AuditsTable({
  projectId,
  audits,
  onChange,
}: {
  projectId: string;
  audits: Audit[];
  onChange?: () => void;
}) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (audits.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground">
        No audits yet. Click <span className="font-medium">Run audit</span> to get started.
      </p>
    );
  }

  // De-duplicate paired runs — one row per run, keyed by the "primary" (production) audit.
  const primary = audits.filter(
    (a) => a.environment === "production" || a.companion_audit_id === null,
  );

  async function handleDelete(audit: Audit) {
    const action = audit.status === "queued" || audit.status === "running" ? "Stop" : "Delete";
    if (!confirm(`${action} this audit?`)) return;
    setBusyId(audit.id);
    setError(null);
    try {
      await auditsApi.delete(audit.id);
      onChange?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : `Failed to ${action.toLowerCase()} audit`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2 text-left">Date</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Verdict</th>
              <th className="px-4 py-2 text-right">Pages</th>
              <th className="px-4 py-2 text-right">Broken</th>
              <th className="px-4 py-2 text-right">SEO</th>
              <th className="px-4 py-2 text-right" aria-label="Actions"></th>
            </tr>
          </thead>
          <tbody>
            {primary.map((a) => (
              <tr key={a.id} className="border-t border-border hover:bg-muted/30">
                <td className="px-4 py-2">
                  <Link
                    href={`/projects/${projectId}/audits/${a.id}`}
                    className="font-medium hover:underline"
                  >
                    {new Date(a.created_at).toLocaleString()}
                  </Link>
                </td>
                <td className="px-4 py-2">
                  <AuditStatusBadge status={a.status} />
                </td>
                <td className="px-4 py-2">
                  <VerdictBadge
                    verdict={a.verdict}
                    pending={a.status === "running" || a.status === "queued"}
                  />
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{a.pages_crawled}</td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {a.broken_links_count > 0 ? (
                    <span className="text-destructive">{a.broken_links_count}</span>
                  ) : (
                    a.broken_links_count
                  )}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {a.seo_score == null ? "—" : a.seo_score}
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => handleDelete(a)}
                    disabled={busyId === a.id}
                    aria-label={
                      a.status === "queued" || a.status === "running"
                        ? "Stop audit"
                        : "Delete audit"
                    }
                    title={
                      a.status === "queued" || a.status === "running"
                        ? "Stop audit"
                        : "Delete audit"
                    }
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
