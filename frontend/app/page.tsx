"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth/auth-context";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  if (loading || user) return null;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6">
      <h1 className="text-4xl font-semibold tracking-tight">SmartLaunch QA</h1>
      <p className="max-w-md text-center text-muted-foreground">
        Pre-launch website QA platform. Run audits, diff staging vs production, ship with
        confidence.
      </p>
      <div className="flex gap-3">
        <Link
          href="/login"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Sign in
        </Link>
        <Link
          href="/register"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          Create account
        </Link>
      </div>
    </main>
  );
}
