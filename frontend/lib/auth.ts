import { api } from "@/lib/api";

export type Role = "admin" | "developer" | "pm" | "qa";

export type User = {
  id: string;
  name: string;
  email: string;
  role: Role;
  created_at: string;
};

export type RegisterInput = { name: string; email: string; password: string };
export type LoginInput = { email: string; password: string };

export const authApi = {
  me: () => api<User>("/auth/me"),
  register: (body: RegisterInput) =>
    api<User>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: LoginInput) =>
    api<User>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => api<void>("/auth/logout", { method: "POST" }),
  refresh: () => api<User>("/auth/refresh", { method: "POST" }),
};
