import { api } from "@/lib/api";

export type AuditStatus = "queued" | "running" | "completed" | "failed";
export type AuditEnvironment = "production" | "staging";
export type Verdict = "go" | "no_go";
export type Severity = "critical" | "warning" | "info" | "ok";
export type DiffChangeType = "added_in_production" | "removed_in_production" | "modified";

export type AuditIssue = {
  id: string;
  page_url: string;
  type: string;
  severity: Severity;
  message: string;
  recommendation: string;
  status_code: number | null;
};

export type Audit = {
  id: string;
  project_id: string;
  environment: AuditEnvironment;
  status: AuditStatus;
  pages_crawled: number;
  broken_links_count: number;
  seo_score: number | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  companion_audit_id: string | null;
  verdict: Verdict | null;
};

export type AuditDetail = Audit & { issues: AuditIssue[] };

export type AuditDiffEntry = {
  id: string;
  page_url: string;
  field: string;
  staging_value: string | null;
  production_value: string | null;
  change_type: DiffChangeType;
  severity: Severity;
};

export type DiffResponse = {
  audit_id: string;
  companion_audit_id: string;
  pair_complete: boolean;
  verdict: Verdict | null;
  diffs: AuditDiffEntry[];
};

export const auditsApi = {
  listForProject: (projectId: string) =>
    api<Audit[]>(`/projects/${projectId}/audits`),
  enqueue: (projectId: string, environment?: AuditEnvironment) =>
    api<Audit[]>(`/projects/${projectId}/audits`, {
      method: "POST",
      body: JSON.stringify(environment ? { environment } : {}),
    }),
  get: (id: string) => api<AuditDetail>(`/audits/${id}`),
  diff: (id: string) => api<DiffResponse>(`/audits/${id}/diff`),
};
