import { apiFetch } from "@/api/client";
import type { Project } from "@/types/api";

export function listProjects() {
  return apiFetch<{ items: Project[]; total: number }>("/api/v1/projects");
}

export function getProject(id: string) {
  return apiFetch<{ project: Project }>(`/api/v1/projects/${id}`);
}

export function createProject(input: { name: string; description?: string }) {
  return apiFetch<{ project: Project }>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateProject(id: string, input: { name?: string; description?: string }) {
  return apiFetch<{ project: Project }>(`/api/v1/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteProject(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/v1/projects/${id}`, { method: "DELETE" });
}
