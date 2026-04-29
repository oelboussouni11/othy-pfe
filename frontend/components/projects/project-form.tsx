"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import type { Project, ProjectCreate, ProjectStatus } from "@/lib/projects";

const STATUSES: ProjectStatus[] = ["draft", "in_progress", "completed", "archived"];

type Props = {
  initial?: Project;
  submitLabel: string;
  onSubmit: (body: ProjectCreate) => Promise<void>;
  onCancel?: () => void;
};

export function ProjectForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [clientName, setClientName] = useState(initial?.client_name ?? "");
  const [productionUrl, setProductionUrl] = useState(initial?.production_url ?? "");
  const [stagingUrl, setStagingUrl] = useState(initial?.staging_url ?? "");
  const [status, setStatus] = useState<ProjectStatus>(initial?.status ?? "draft");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        client_name: clientName.trim() || null,
        production_url: productionUrl.trim(),
        staging_url: stagingUrl.trim() || null,
        status,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <Field
        id="name"
        label="Project name"
        value={name}
        onChange={setName}
        required
        autoFocus
      />
      <Field
        id="client_name"
        label="Client (optional)"
        value={clientName}
        onChange={setClientName}
      />
      <Field
        id="production_url"
        label="Production URL"
        type="url"
        placeholder="https://example.com"
        value={productionUrl}
        onChange={setProductionUrl}
        required
      />
      <Field
        id="staging_url"
        label="Staging URL (optional)"
        type="url"
        placeholder="https://staging.example.com"
        value={stagingUrl}
        onChange={setStagingUrl}
      />
      <div className="space-y-1.5">
        <label htmlFor="status" className="block text-sm font-medium">
          Status
        </label>
        <select
          id="status"
          value={status}
          onChange={(e) => setStatus(e.target.value as ProjectStatus)}
          className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus:ring-2 focus:ring-ring"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Saving…" : submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
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
