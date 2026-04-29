import { AuditStatusBadge } from "@/components/audits/audit-status-badge";
import { VerdictBadge } from "@/components/audits/verdict-badge";
import type { AuditDetail } from "@/lib/audits";

export function SummaryCard({ audit }: { audit: AuditDetail }) {
  const isPending = audit.status === "queued" || audit.status === "running";
  return (
    <section className="rounded-lg border border-border bg-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {audit.environment} · {new Date(audit.created_at).toLocaleString()}
          </p>
          <div className="flex items-center gap-3">
            <VerdictBadge verdict={audit.verdict} pending={isPending} size="lg" />
            <AuditStatusBadge status={audit.status} />
          </div>
        </div>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Pages crawled" value={audit.pages_crawled} />
        <Stat
          label="Broken links"
          value={audit.broken_links_count}
          tone={audit.broken_links_count > 0 ? "destructive" : "default"}
        />
        <Stat label="SEO score" value={audit.seo_score ?? "—"} suffix={audit.seo_score == null ? "" : "/100"} />
        <Stat label="Issues" value={audit.issues.length} />
      </dl>

      {audit.error_message && (
        <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {audit.error_message}
        </p>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  suffix = "",
  tone = "default",
}: {
  label: string;
  value: string | number;
  suffix?: string;
  tone?: "default" | "destructive";
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd
        className={
          tone === "destructive"
            ? "mt-0.5 text-2xl font-semibold tabular-nums text-destructive"
            : "mt-0.5 text-2xl font-semibold tabular-nums"
        }
      >
        {value}
        {suffix && <span className="ml-1 text-base font-normal text-muted-foreground">{suffix}</span>}
      </dd>
    </div>
  );
}
