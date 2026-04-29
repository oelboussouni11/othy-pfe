"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Protected } from "@/components/auth/protected";
import { ProjectForm } from "@/components/projects/project-form";
import { StatusBadge } from "@/components/projects/status-badge";
import { ApiError } from "@/lib/api";
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
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    projectsApi
      .get(id)
      .then(setProject)
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Failed to load project"));
  }, [id]);

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
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-4 px-6 py-12">
        <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
          ← Projects
        </Link>
        <p className="text-sm text-destructive">{error}</p>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl px-6 py-12 text-sm text-muted-foreground">
        Loading…
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-6 py-12">
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
        <StatusBadge status={project.status} />
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
            <Row label="Created">
              {new Date(project.created_at).toLocaleDateString()}
            </Row>
          </section>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3">
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
