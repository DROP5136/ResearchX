import axios, { AxiosError, type AxiosInstance } from "axios";
import { env } from "../config/env";
import { AppError } from "../utils/errors";

export interface FastApiStartRequest {
  query: string;
  depth?: "quick" | "standard" | "deep";
  max_iterations?: number | null;
  enable_web_search?: boolean;
  enable_pdf_rag?: boolean;
  enable_document_research?: boolean;
  enable_analysis?: boolean;
  mock_mode?: boolean | null;
  requirements?: string[];
  pdf_paths?: string[];
  document_ids?: string[];
}

export interface FastApiStartResponse {
  research_id: string;
  status: string;
}

export interface FastApiStatusResponse {
  research_id: string;
  status: string;
  current_stage?: string | null;
  progress?: number;
  message?: string | null;
  errors?: string[];
}

export interface FastApiResultResponse {
  research_id: string;
  query?: string;
  status: string;
  current_stage?: string | null;
  progress?: number;
  report?: Record<string, unknown> | null;
  sources?: unknown[];
  claims?: unknown[];
  contradictions?: unknown[];
  analysis?: unknown[];
  charts?: unknown[];
  evidence?: unknown[];
  errors?: string[];
  metadata?: Record<string, unknown>;
}

function mapAxiosError(err: unknown, fallbackCode: string): AppError {
  if (err instanceof AxiosError) {
    if (err.code === "ECONNABORTED") {
      return new AppError("TIMEOUT", "FastAPI request timed out", 504);
    }
    if (err.code === "ECONNREFUSED" || err.message.includes("Network Error")) {
      return new AppError("PROVIDER_UNAVAILABLE", "FastAPI AI service is unavailable", 502);
    }
    const status = err.response?.status;
    const data = err.response?.data as { error?: { code?: string; message?: string } } | undefined;
    const message = data?.error?.message || err.message || "FastAPI request failed";
    if (status && status >= 400 && status < 500) {
      return new AppError(data?.error?.code || "FASTAPI_CLIENT_ERROR", message, status);
    }
    return new AppError(data?.error?.code || fallbackCode, message, status && status >= 500 ? 502 : 502);
  }
  return new AppError(fallbackCode, "FastAPI request failed", 502);
}

export class FastApiService {
  private client: AxiosInstance;

  constructor(baseURL = env.FASTAPI_URL, timeoutMs = 30_000) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (env.AI_SERVICE_TOKEN) {
      headers["X-Internal-Token"] = env.AI_SERVICE_TOKEN;
    }
    this.client = axios.create({
      baseURL: baseURL.replace(/\/$/, ""),
      timeout: timeoutMs,
      headers,
    });
  }

  async startResearch(payload: FastApiStartRequest): Promise<FastApiStartResponse> {
    try {
      const { data } = await this.client.post<FastApiStartResponse>("/api/v1/research", payload);
      if (!data?.research_id) {
        throw new AppError("MALFORMED_RESPONSE", "FastAPI did not return research_id", 502);
      }
      return data;
    } catch (err) {
      if (err instanceof AppError) throw err;
      throw mapAxiosError(err, "FASTAPI_START_FAILED");
    }
  }

  async getResearchStatus(fastApiResearchId: string): Promise<FastApiStatusResponse> {
    try {
      const { data } = await this.client.get<FastApiStatusResponse>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}/status`
      );
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_STATUS_FAILED");
    }
  }

  async getResearchResult(fastApiResearchId: string): Promise<FastApiResultResponse> {
    try {
      const { data } = await this.client.get<FastApiResultResponse>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}`
      );
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_RESULT_FAILED");
    }
  }

  async getSources(fastApiResearchId: string): Promise<unknown[]> {
    try {
      const { data } = await this.client.get<unknown[]>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}/sources`
      );
      return Array.isArray(data) ? data : [];
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_SOURCES_FAILED");
    }
  }

  async getClaims(fastApiResearchId: string): Promise<unknown[]> {
    try {
      const { data } = await this.client.get<unknown[]>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}/claims`
      );
      return Array.isArray(data) ? data : [];
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_CLAIMS_FAILED");
    }
  }

  async getReport(fastApiResearchId: string): Promise<Record<string, unknown>> {
    try {
      const { data } = await this.client.get<Record<string, unknown>>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}/report`
      );
      return data || {};
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_REPORT_FAILED");
    }
  }

  async getLatestEvaluation(): Promise<unknown> {
    try {
      const { data } = await this.client.get("/api/v1/evaluation/latest");
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_EVAL_LATEST_FAILED");
    }
  }

  async runEvaluation(payload: { mock_mode?: boolean; limit?: number } = {}): Promise<unknown> {
    try {
      const { data } = await this.client.post("/api/v1/evaluation/run", payload);
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_EVAL_FAILED");
    }
  }

  async health(): Promise<unknown> {
    try {
      const { data } = await this.client.get("/health");
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_HEALTH_FAILED");
    }
  }

  async processDocument(payload: {
    path: string;
    document_id: string;
    original_filename?: string;
    force?: boolean;
  }): Promise<{
    document_id: string;
    status: string;
    page_count: number;
    chunk_count: number;
    skipped_reembed: boolean;
    stage: string;
  }> {
    try {
      const { data } = await this.client.post("/api/v1/documents/process", payload, {
        timeout: 120_000,
      });
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_DOCUMENT_PROCESS_FAILED");
    }
  }

  async deleteDocument(documentId: string): Promise<unknown> {
    try {
      const { data } = await this.client.post("/api/v1/documents/delete", {
        document_id: documentId,
      });
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_DOCUMENT_DELETE_FAILED");
    }
  }

  async cancelResearch(fastApiResearchId: string): Promise<FastApiStatusResponse> {
    try {
      const { data } = await this.client.post<FastApiStatusResponse>(
        `/api/v1/research/${encodeURIComponent(fastApiResearchId)}/cancel`
      );
      return data;
    } catch (err) {
      throw mapAxiosError(err, "FASTAPI_CANCEL_FAILED");
    }
  }
}

export const fastApiService = new FastApiService();
