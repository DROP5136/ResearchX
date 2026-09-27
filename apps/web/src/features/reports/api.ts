import { apiFetch } from "@/api/client";
import type { SavedReport } from "@/types/api";

export function listSavedReports() {
  return apiFetch<{ items: SavedReport[]; total: number }>("/api/v1/saved-reports");
}
