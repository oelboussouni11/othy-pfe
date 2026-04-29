"use client";

import { Protected } from "@/components/auth/protected";
import { useAuth } from "@/components/auth/auth-context";

export default function DashboardPage() {
  return (
    <Protected>
      <DashboardContent />
    </Protected>
  );
}

function DashboardContent() {
  const { user, logout } = useAuth();
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-6 py-12">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <button
          onClick={() => logout()}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
        >
          Sign out
        </button>
      </header>
      <section className="rounded-lg border border-border bg-card p-6">
        <p className="text-sm text-muted-foreground">Signed in as</p>
        <p className="mt-1 text-lg font-medium">{user?.name}</p>
        <p className="text-sm text-muted-foreground">{user?.email}</p>
        <p className="mt-3 inline-flex rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
          {user?.role}
        </p>
      </section>
      <p className="text-xs text-muted-foreground">
        Phase 2 placeholder — projects list lands in Phase 3.
      </p>
    </main>
  );
}
