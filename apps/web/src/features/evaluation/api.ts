import { apiFetch } from "@/api/client";
import type { EvaluationLatest } from "@/types/api";

export function getLatestEvaluation() {
  return apiFetch<EvaluationLatest>("/api/v1/evaluation/latest");
}

export function runEvaluation(input: { mockMode?: boolean; limit?: number } = {}) {
  return apiFetch<Record<string, unknown>>("/api/v1/evaluation/run", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
