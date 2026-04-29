import { api } from "@/lib/api";

export type ProjectStatus = "draft" | "in_progress" | "completed" | "archived";

export type Project = {
  id: string;
  name: string;
  client_name: string | null;
  production_url: string;
  staging_url: string | null;
  status: ProjectStatus;
  owner_id: string;
  created_at: string;
};

export type ProjectCreate = {
  name: string;
  client_name?: string | null;
  production_url: string;
  staging_url?: string | null;
  status?: ProjectStatus;
};

export type ProjectUpdate = Partial<ProjectCreate>;

export const projectsApi = {
  list: () => api<Project[]>("/projects"),
  get: (id: string) => api<Project>(`/projects/${id}`),
  create: (body: ProjectCreate) =>
    api<Project>("/projects", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: ProjectUpdate) =>
    api<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (id: string) => api<void>(`/projects/${id}`, { method: "DELETE" }),
};
