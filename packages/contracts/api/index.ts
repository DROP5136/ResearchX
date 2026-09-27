/**
 * Shared API contracts between ResearchX web client and Express server.
 * Python/Pydantic schemas remain in apps/ai-service (different runtime).
 */

export type User = {
  id: string;
  name: string;
  email: string;
  createdAt?: string;
  updatedAt?: string;
};

export type Project = {
  id: string;
  userId: string;
  name: string;
  description: string;
  createdAt?: string;
  updatedAt?: string;
  sessionCount?: number;
};

export type ResearchSession = {
  id: string;
  projectId: string;
  userId: string;
  query: string;
  status: string;
  currentStage?: string | null;
  progress: number;
  fastApiResearchId: string;
  completedAt?: string | null;
  error?: string | null;
  createdAt?: string;
  updatedAt?: string;
  report?: ReportPayload | null;
  sources?: Source[];
  claims?: Claim[];
  contradictions?: Contradiction[];
  analysis?: AnalysisItem[];
  charts?: ChartSpec[];
  evidence?: Evidence[];
};

export type ReportPayload = {
  title?: string;
  query?: string;
  executive_summary?: string;
  methodology?: string;
  key_findings?: string[];
  detailed_analysis?: string;
  limitations?: string[];
  conclusion?: string;
  markdown?: string;
  references?: Array<Record<string, string>>;
  charts?: ChartSpec[];
  chart_data?: ChartSpec[];
  status_note?: string;
};

export type Source = {
  source_id: string;
  title?: string;
  url?: string;
  domain?: string;
  published_at?: string | null;
  source_type?: string;
  relevance_score?: number;
  quality_score?: number;
  authority_score?: number;
  snippet?: string;
  metadata?: {
    source_kind?: string;
    document_id?: string;
    page?: number;
    chunk_id?: string;
    filename?: string;
    citation?: string;
    [key: string]: unknown;
  };
};

export type Claim = {
  claim_id: string;
  claim: string;
  verification_status?: string;
  confidence?: number;
  evidence_ids?: string[];
  source_ids?: string[];
  contradiction_status?: string;
  notes?: string;
};

export type Contradiction = {
  contradiction_id?: string;
  claim_ids?: string[];
  description?: string;
  sources?: string[];
  possible_explanation?: string;
  status?: string;
};

export type Evidence = {
  evidence_id: string;
  source_id: string;
  text: string;
};

export type AnalysisItem = {
  analysis_type?: string;
  metric?: string;
  formula?: string;
  result?: unknown;
  interpretation?: string;
  status?: string;
  chart_data?: ChartSpec;
  chart?: ChartSpec;
};

export type ChartSpec = {
  chart_type?: string;
  type?: string;
  title?: string;
  x_axis?: string;
  y_axis?: string;
  x?: string;
  y?: string;
  data?: Array<Record<string, unknown>>;
  series?: Array<{ name: string; data?: unknown[] } | string>;
};

export type SavedReport = {
  id: string;
  researchSessionId: string;
  projectId: string;
  title: string;
  query: string;
  createdAt?: string;
  research?: { status?: string; progress?: number; completedAt?: string };
};

export type EvaluationLatest = {
  overall?: Record<string, number>;
  performance?: Record<string, number>;
  by_category?: Record<string, Record<string, number>>;
  failures?: Array<Record<string, unknown>>;
  n?: number;
  mode?: string;
  generated_at?: string;
  results?: Array<Record<string, unknown>>;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};
