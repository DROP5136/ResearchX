import { apiFetch } from "@/api/client";
import type { ResearchSession } from "@/types/api";

export type StartResearchInput = {
  projectId: string;
  query: string;
  depth?: "quick" | "standard" | "deep";
  maxIterations?: number;
  enableWebSearch?: boolean;
  enablePdfRag?: boolean;
  enableDocumentResearch?: boolean;
  enableAnalysis?: boolean;
  mockMode?: boolean;
  requirements?: string[];
  documentIds?: string[];
};

export function startResearch(input: StartResearchInput) {
  return apiFetch<{ research: ResearchSession }>("/api/v1/research", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listResearch(params: {
  projectId?: string;
  status?: string;
  page?: number;
  limit?: number;
} = {}) {
  const q = new URLSearchParams();
  if (params.projectId) q.set("projectId", params.projectId);
  if (params.status) q.set("status", params.status);
  if (params.page) q.set("page", String(params.page));
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<{ items: ResearchSession[]; page: number; limit: number; total: number }>(
    `/api/v1/research${qs ? `?${qs}` : ""}`
  );
}

export function getResearch(id: string) {
  return apiFetch<{ research: ResearchSession }>(`/api/v1/research/${id}`);
}

export function getResearchStatus(id: string) {
  return apiFetch<{
    researchId: string;
    fastApiResearchId: string;
    status: string;
    currentStage?: string;
    progress: number;
    error?: string | null;
  }>(`/api/v1/research/${id}/status`);
}

export function getResearchSources(id: string) {
  return apiFetch<{ items: unknown[] }>(`/api/v1/research/${id}/sources`);
}

export function getResearchClaims(id: string) {
  return apiFetch<{ items: unknown[] }>(`/api/v1/research/${id}/claims`);
}

export function getResearchReport(id: string) {
  return apiFetch<{ report: Record<string, unknown> }>(`/api/v1/research/${id}/report`);
}

export function saveResearch(id: string) {
  return apiFetch<{ savedReport: unknown }>(`/api/v1/research/${id}/save`, { method: "POST" });
}

export function unsaveResearch(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/v1/research/${id}/save`, { method: "DELETE" });
}
