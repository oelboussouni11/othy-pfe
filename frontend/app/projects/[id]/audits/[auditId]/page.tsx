"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Protected } from "@/components/auth/protected";
import { DiffTab } from "@/components/audits/diff-tab";
import { IssuesTab } from "@/components/audits/issues-tab";
import { PagesTab } from "@/components/audits/pages-tab";
import { SummaryCard } from "@/components/audits/summary-card";
import { ApiError, API_URL } from "@/lib/api";
import { auditsApi, type AuditDetail } from "@/lib/audits";
import { cn } from "@/lib/utils";

type Tab = "issues" | "diff" | "pages";

export default function AuditDetailPage() {
  return (
    <Protected>
      <AuditDetail />
    </Protected>
  );
}

function AuditDetail() {
  const { id: projectId, auditId } = useParams<{ id: string; auditId: string }>();
  const router = useRouter();
  const [audit, setAudit] = useState<AuditDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("issues");
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(() => {
    if (!auditId) return Promise.resolve();
    return auditsApi
      .get(auditId)
      .then(setAudit)
      .catch((e) =>
        setError(e instanceof ApiError ? e.detail : "Failed to load audit"),
      );
  }, [auditId]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll every 2s while the audit is still running.
  useEffect(() => {
    if (!audit) return;
    if (audit.status !== "queued" && audit.status !== "running") return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [audit, load]);

  if (error && !audit) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 px-6 py-12">
        <BackLink projectId={projectId} />
        <p className="text-sm text-destructive">{error}</p>
      </main>
    );
  }
  if (!audit) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl px-6 py-12 text-sm text-muted-foreground">
        Loading…
      </main>
    );
  }

  const isPaired = audit.companion_audit_id != null;

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <BackLink projectId={projectId} />
        <div className="flex flex-wrap gap-2">
          <a
            href={`${API_URL}/audits/${audit.id}/export.html`}
            target="_blank"
            rel="noreferrer noopener"
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Export HTML
          </a>
          <button
            onClick={async () => {
              const action =
                audit.status === "queued" || audit.status === "running" ? "Stop" : "Delete";
              if (!confirm(`${action} this audit?`)) return;
              setDeleting(true);
              try {
                await auditsApi.delete(audit.id);
                router.replace(`/projects/${projectId}`);
              } catch (e) {
                setError(e instanceof ApiError ? e.detail : "Failed to delete audit");
                setDeleting(false);
              }
            }}
            disabled={deleting}
            className="rounded-md border border-destructive/40 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-60"
          >
            {deleting
              ? "…"
              : audit.status === "queued" || audit.status === "running"
                ? "Stop"
                : "Delete"}
          </button>
        </div>
      </div>

      <SummaryCard audit={audit} />

      <nav className="flex border-b border-border">
        <TabButton active={tab === "issues"} onClick={() => setTab("issues")}>
          Issues ({audit.issues.length})
        </TabButton>
        {isPaired && (
          <TabButton active={tab === "diff"} onClick={() => setTab("diff")}>
            Diff
          </TabButton>
        )}
        <TabButton active={tab === "pages"} onClick={() => setTab("pages")}>
          Pages
        </TabButton>
      </nav>

      <div>
        {tab === "issues" && <IssuesTab issues={audit.issues} />}
        {tab === "diff" && isPaired && <DiffTab auditId={audit.id} />}
        {tab === "pages" && <PagesTab issues={audit.issues} />}
      </div>
    </main>
  );
}

function BackLink({ projectId }: { projectId: string }) {
  return (
    <Link
      href={`/projects/${projectId}`}
      className="text-sm text-muted-foreground hover:underline"
    >
      ← Project
    </Link>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "border-b-2 px-4 py-2 text-sm font-medium transition",
        active
          ? "border-foreground text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}
