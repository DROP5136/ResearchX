import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | Date | null): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPct(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const n = value <= 1 ? value * 100 : value;
  return `${n.toFixed(1)}%`;
}

const STAGE_LABELS: Record<string, string> = {
  queued: "Queued",
  planning: "Planning",
  researching: "Researching",
  extracting_evidence: "Collecting evidence",
  evidence: "Collecting evidence",
  fact_checking: "Fact checking",
  analyzing: "Analyzing",
  writing: "Writing",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  canceled: "Cancelled",
};

export function stageLabel(stage?: string | null): string {
  if (!stage) return "Unknown";
  const key = stage.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (STAGE_LABELS[key]) return STAGE_LABELS[key];
  return key
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
