"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/auth-context";
import { ApiError } from "@/lib/api";

type Mode = "login" | "register";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { login, register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === "register";

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isRegister) {
        await register({ name, email, password });
      } else {
        await login({ email, password });
      }
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Something went wrong. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-5 rounded-lg border border-border bg-card p-8 shadow-sm"
      >
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {isRegister ? "Create account" : "Sign in"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isRegister
              ? "Get started with SmartLaunch QA."
              : "Welcome back. Sign in to continue."}
          </p>
        </header>

        {isRegister && (
          <Field
            label="Name"
            id="name"
            value={name}
            onChange={setName}
            autoComplete="name"
            required
          />
        )}
        <Field
          label="Email"
          id="email"
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          required
        />
        <Field
          label="Password"
          id="password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={isRegister ? "new-password" : "current-password"}
          minLength={8}
          required
        />

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting
            ? isRegister
              ? "Creating…"
              : "Signing in…"
            : isRegister
              ? "Create account"
              : "Sign in"}
        </button>

        <p className="text-center text-sm text-muted-foreground">
          {isRegister ? (
            <>
              Already have an account?{" "}
              <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
                Sign in
              </Link>
            </>
          ) : (
            <>
              No account yet?{" "}
              <Link href="/register" className="text-foreground underline-offset-4 hover:underline">
                Create one
              </Link>
            </>
          )}
        </p>
      </form>
    </main>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  ...rest
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "id" | "value" | "onChange" | "type">) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus:ring-2 focus:ring-ring"
        {...rest}
      />
    </div>
  );
}
