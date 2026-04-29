"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Protected } from "@/components/auth/protected";
import { AuditsTable } from "@/components/audits/audits-table";
import { VerdictBadge } from "@/components/audits/verdict-badge";
import { ProjectForm } from "@/components/projects/project-form";
import { StatusBadge } from "@/components/projects/status-badge";
import { ApiError } from "@/lib/api";
import { auditsApi, type Audit } from "@/lib/audits";
import { projectsApi, type Project } from "@/lib/projects";

export default function ProjectDetailPage() {
  return (
    <Protected>
      <ProjectDetail />
    </Protected>
  );
}

function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [running, setRunning] = useState(false);

  const loadAudits = useCallback(() => {
    if (!id) return Promise.resolve();
    return auditsApi.listForProject(id).then(setAudits).catch(() => undefined);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    projectsApi
      .get(id)
      .then(setProject)
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Failed to load project"));
    loadAudits();
  }, [id, loadAudits]);

  // Poll while any audit is in-flight so the table updates without a manual refresh.
  useEffect(() => {
    const inFlight = audits.some((a) => a.status === "queued" || a.status === "running");
    if (!inFlight) return;
    const t = setInterval(loadAudits, 2000);
    return () => clearInterval(t);
  }, [audits, loadAudits]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      await auditsApi.enqueue(id);
      await loadAudits();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to start audit");
    } finally {
      setRunning(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this project? This cannot be undone.")) return;
    setDeleting(true);
    setError(null);
    try {
      await projectsApi.delete(id);
      router.replace("/projects");
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to delete");
      setDeleting(false);
    }
  }

  if (error && !project) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-4 px-6 py-12">
        <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
          ← Projects
        </Link>
        <p className="text-sm text-destructive">{error}</p>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl px-6 py-12 text-sm text-muted-foreground">
        Loading…
      </main>
    );
  }

  const lastCompleted = audits.find((a) => a.status === "completed" && a.environment === "production");

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
        ← Projects
      </Link>

      <header className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
          {project.client_name && (
            <p className="text-sm text-muted-foreground">{project.client_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastCompleted && <VerdictBadge verdict={lastCompleted.verdict} size="lg" />}
          <StatusBadge status={project.status} />
        </div>
      </header>

      {!editing ? (
        <>
          <section className="rounded-lg border border-border bg-card p-5 text-sm">
            <Row label="Production">
              <a
                href={project.production_url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-foreground underline-offset-4 hover:underline"
              >
                {project.production_url}
              </a>
            </Row>
            <Row label="Staging">
              {project.staging_url ? (
                <a
                  href={project.staging_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-foreground underline-offset-4 hover:underline"
                >
                  {project.staging_url}
                </a>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </Row>
            <Row label="Created">{new Date(project.created_at).toLocaleDateString()}</Row>
          </section>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleRun}
              disabled={running}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {running ? "Starting…" : "Run audit"}
            </button>
            <button
              onClick={() => setEditing(true)}
              className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
            >
              Edit
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-md border border-destructive/40 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-60"
            >
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </div>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">Audits</h2>
            <AuditsTable projectId={project.id} audits={audits} />
          </section>
        </>
      ) : (
        <ProjectForm
          initial={project}
          submitLabel="Save changes"
          onSubmit={async (body) => {
            const updated = await projectsApi.update(project.id, body);
            setProject(updated);
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      )}
    </main>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-center gap-3 border-b border-border py-2 last:border-0">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="truncate">{children}</span>
    </div>
  );
}
