"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Protected } from "@/components/auth/protected";
import { StatusBadge } from "@/components/projects/status-badge";
import { ApiError } from "@/lib/api";
import { projectsApi, type Project } from "@/lib/projects";

export default function ProjectsPage() {
  return (
    <Protected>
      <ProjectsList />
    </Protected>
  );
}

function ProjectsList() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    projectsApi
      .list()
      .then(setProjects)
      .catch((e) => {
        setError(e instanceof ApiError ? e.detail : "Failed to load projects");
        setProjects([]);
      });
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-12">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Sites you’re auditing for pre-launch QA.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          New project
        </Link>
      </header>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {projects === null ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : projects.length === 0 ? (
        <EmptyState />
      ) : (
        <ProjectsGrid projects={projects} />
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <section className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border p-12 text-center">
      <h2 className="text-lg font-medium">No projects yet</h2>
      <p className="max-w-sm text-sm text-muted-foreground">
        Add a project to start running pre-launch audits and diff staging vs production.
      </p>
      <Link
        href="/projects/new"
        className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
      >
        Create your first project
      </Link>
    </section>
  );
}

function ProjectsGrid({ projects }: { projects: Project[] }) {
  return (
    <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {projects.map((p) => (
        <li key={p.id}>
          <Link
            href={`/projects/${p.id}`}
            className="block rounded-lg border border-border bg-card p-5 transition hover:bg-muted/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <p className="truncate font-medium">{p.name}</p>
                {p.client_name && (
                  <p className="truncate text-sm text-muted-foreground">{p.client_name}</p>
                )}
              </div>
              <StatusBadge status={p.status} />
            </div>
            <p className="mt-3 truncate text-xs text-muted-foreground">{p.production_url}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
