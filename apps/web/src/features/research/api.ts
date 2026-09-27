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
    startedAt?: string | null;
    completedAt?: string | null;
    elapsedMs?: number | null;
    retryCount?: number;
  }>(`/api/v1/research/${id}/status`);
}

export type ResearchProgressEvent = {
  researchId: string;
  status: string;
  currentStage?: string | null;
  progress: number;
  error?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
  elapsedMs?: number | null;
};

/**
 * Subscribe to research progress over SSE (Authorization via fetch).
 * Falls back to polling if the stream errors.
 */
export function subscribeResearchEvents(
  id: string,
  handlers: {
    onProgress?: (data: ResearchProgressEvent) => void;
    onDone?: (data: ResearchProgressEvent) => void;
    onError?: (err: unknown) => void;
  }
): () => void {
  const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "";
  const token = localStorage.getItem("rx_token");
  const controller = new AbortController();

  void (async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/research/${id}/events`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        handlers.onError?.(new Error(`SSE failed: ${res.status}`));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let eventName = "message";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";
        for (const chunk of chunks) {
          const lines = chunk.split("\n");
          let dataLine = "";
          for (const line of lines) {
            if (line.startsWith("event:")) eventName = line.slice(6).trim();
            if (line.startsWith("data:")) dataLine += line.slice(5).trim();
          }
          if (!dataLine) continue;
          try {
            const data = JSON.parse(dataLine) as ResearchProgressEvent;
            if (eventName === "progress") handlers.onProgress?.(data);
            if (eventName === "done") handlers.onDone?.(data);
            if (eventName === "error") handlers.onError?.(data);
          } catch {
            /* ignore malformed */
          }
          eventName = "message";
        }
      }
    } catch (err) {
      if ((err as { name?: string })?.name !== "AbortError") {
        handlers.onError?.(err);
      }
    }
  })();

  return () => controller.abort();
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

export function cancelResearch(id: string) {
  return apiFetch<{ research: ResearchSession }>(`/api/v1/research/${id}/cancel`, {
    method: "POST",
  });
}
