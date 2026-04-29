"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Protected } from "@/components/auth/protected";
import { ProjectForm } from "@/components/projects/project-form";
import { projectsApi } from "@/lib/projects";

export default function NewProjectPage() {
  return (
    <Protected>
      <NewProject />
    </Protected>
  );
}

function NewProject() {
  const router = useRouter();
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col gap-6 px-6 py-12">
      <div className="space-y-1">
        <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
          ← Projects
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">New project</h1>
      </div>
      <ProjectForm
        submitLabel="Create project"
        onSubmit={async (body) => {
          const created = await projectsApi.create(body);
          router.replace(`/projects/${created.id}`);
        }}
        onCancel={() => router.push("/projects")}
      />
    </main>
  );
}
