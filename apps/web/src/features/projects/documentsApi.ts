import { apiFetch } from "@/api/client";

export type ProjectDocument = {
  id: string;
  documentId: string;
  projectId: string;
  filename: string;
  originalFilename: string;
  mimeType: string;
  size: number;
  status: "uploaded" | "processing" | "ready" | "failed";
  stage?: string | null;
  progress?: number | null;
  pageCount?: number | null;
  chunkCount?: number | null;
  embeddingStatus?: string | null;
  error?: string | null;
  uploadedAt?: string;
  processedAt?: string | null;
};

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("rx_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function listDocuments(projectId: string) {
  return apiFetch<{ items: ProjectDocument[] }>(`/api/v1/projects/${projectId}/documents`);
}

export async function uploadDocuments(projectId: string, files: File[]) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(
    `${(import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || ""}/api/v1/projects/${projectId}/documents`,
    {
      method: "POST",
      headers: authHeaders(),
      body: form,
    }
  );
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } })?.error;
    throw new Error(err?.message || res.statusText || "Upload failed");
  }
  return data as {
    items: Array<{ documentId: string; status: string; filename: string }>;
    documentId: string;
    status: string;
  };
}

export function getDocumentStatus(id: string) {
  return apiFetch<{
    documentId: string;
    status: string;
    progress: number | null;
    stage: string | null;
    pageCount?: number | null;
    chunkCount?: number | null;
    error?: string | null;
  }>(`/api/v1/documents/${id}/status`);
}

export function retryDocument(id: string) {
  return apiFetch<{ documentId: string; status: string }>(`/api/v1/documents/${id}/retry`, {
    method: "POST",
  });
}

export function deleteDocument(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/v1/documents/${id}`, { method: "DELETE" });
}
