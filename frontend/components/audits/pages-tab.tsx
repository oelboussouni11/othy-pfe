import type { AuditIssue } from "@/lib/audits";

/**
 * Pages tab — derived from issues since we don't (yet) persist a per-page snapshot.
 * Groups issues by page_url and shows the issue counts per severity.
 */
export function PagesTab({ issues }: { issues: AuditIssue[] }) {
  const byPage = new Map<
    string,
    { critical: number; warning: number; info: number; status_codes: Set<number> }
  >();

  for (const i of issues) {
    if (!byPage.has(i.page_url)) {
      byPage.set(i.page_url, {
        critical: 0,
        warning: 0,
        info: 0,
        status_codes: new Set(),
      });
    }
    const row = byPage.get(i.page_url)!;
    if (i.severity === "critical") row.critical++;
    else if (i.severity === "warning") row.warning++;
    else if (i.severity === "info") row.info++;
    if (i.status_code != null) row.status_codes.add(i.status_code);
  }

  if (byPage.size === 0) {
    return (
      <p className="rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground">
        No pages with issues. Either the audit found nothing or it hasn’t finished crawling.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-2 text-left">Page</th>
            <th className="px-4 py-2 text-right">Critical</th>
            <th className="px-4 py-2 text-right">Warning</th>
            <th className="px-4 py-2 text-right">Info</th>
            <th className="px-4 py-2 text-right">Statuses</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(byPage.entries()).map(([url, row]) => (
            <tr key={url} className="border-t border-border">
              <td className="px-4 py-2 font-mono text-xs break-all">{url}</td>
              <td className="px-4 py-2 text-right tabular-nums">
                {row.critical > 0 ? (
                  <span className="text-destructive">{row.critical}</span>
                ) : (
                  row.critical
                )}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">{row.warning}</td>
              <td className="px-4 py-2 text-right tabular-nums">{row.info}</td>
              <td className="px-4 py-2 text-right text-xs font-mono text-muted-foreground">
                {row.status_codes.size > 0
                  ? Array.from(row.status_codes).join(", ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
