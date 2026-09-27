import type { Response, NextFunction } from "express";
import { Project } from "../models/Project";
import { ResearchSession } from "../models/ResearchSession";
import { SavedReport } from "../models/SavedReport";
import type { AuthRequest } from "../middleware/auth";
import { fastApiService } from "../services/fastApiService";
import { AppError } from "../utils/errors";
import { toObjectId } from "../utils/helpers";

function serializeSession(
  s: {
    _id: unknown;
    projectId: unknown;
    userId: unknown;
    query: string;
    status: string;
    currentStage?: string | null;
    progress?: number;
    completedAt?: Date | null;
    fastApiResearchId: string;
    report?: unknown;
    sources?: unknown[];
    claims?: unknown[];
    contradictions?: unknown[];
    analysis?: unknown[];
    charts?: unknown[];
    evidence?: unknown[];
    error?: string | null;
    createdAt?: Date;
    updatedAt?: Date;
  },
  opts: { includePayload?: boolean } = {}
) {
  const base = {
    id: String(s._id),
    projectId: String(s.projectId),
    userId: String(s.userId),
    query: s.query,
    status: s.status,
    currentStage: s.currentStage || null,
    progress: s.progress ?? 0,
    fastApiResearchId: s.fastApiResearchId,
    completedAt: s.completedAt || null,
    error: s.error || null,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
  };
  if (!opts.includePayload) return base;
  return {
    ...base,
    report: s.report ?? null,
    sources: s.sources || [],
    claims: s.claims || [],
    contradictions: s.contradictions || [],
    analysis: s.analysis || [],
    charts: s.charts || [],
    evidence: s.evidence || [],
  };
}

async function ownedSession(userId: string, id: string) {
  const session = await ResearchSession.findOne({ _id: id, userId });
  if (!session) {
    throw new AppError("RESEARCH_NOT_FOUND", "Research session not found", 404);
  }
  return session;
}

function mapPipelineStatus(status: string | undefined | null): string {
  const s = (status || "").toLowerCase();
  if (!s) return "running";
  if (s.includes("fail")) return "failed";
  if (s === "started") return "started";
  if (s.includes("completed") || s.includes("insufficient")) return "completed";
  return "running";
}

async function syncFromFastApi(session: InstanceType<typeof ResearchSession>) {
  const status = await fastApiService.getResearchStatus(session.fastApiResearchId);
  const mapped = mapPipelineStatus(status.status);
  session.status = mapped;
  session.currentStage = status.current_stage || session.currentStage;
  session.progress = typeof status.progress === "number" ? status.progress : session.progress;
  if (status.errors?.length) {
    session.error = status.errors.join("; ");
  }

  if (mapped === "completed" || mapped === "failed") {
    if (mapped === "completed" && !session.report) {
      const result = await fastApiService.getResearchResult(session.fastApiResearchId);
      session.report = result.report ?? null;
      session.sources = (result.sources as unknown[]) || [];
      session.claims = (result.claims as unknown[]) || [];
      session.contradictions = (result.contradictions as unknown[]) || [];
      session.analysis = (result.analysis as unknown[]) || [];
      session.charts = (result.charts as unknown[]) || [];
      session.evidence = (result.evidence as unknown[]) || [];
      if (result.errors?.length) session.error = result.errors.join("; ");
    }
    if (!session.completedAt) {
      session.completedAt = new Date();
    }
    session.progress = 100;
  }

  await session.save();
  return session;
}

export async function startResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const body = req.body as {
      projectId: string;
      query: string;
      depth?: "quick" | "standard" | "deep";
      maxIterations?: number;
      enableWebSearch?: boolean;
      enablePdfRag?: boolean;
      enableAnalysis?: boolean;
      mockMode?: boolean;
      requirements?: string[];
    };

    const project = await Project.findOne({
      _id: body.projectId,
      userId: req.userId,
    });
    if (!project) {
      throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
    }

    const started = await fastApiService.startResearch({
      query: body.query,
      depth: body.depth || "standard",
      max_iterations: body.maxIterations ?? null,
      enable_web_search: body.enableWebSearch ?? true,
      enable_pdf_rag: body.enablePdfRag ?? false,
      enable_analysis: body.enableAnalysis ?? true,
      mock_mode: body.mockMode ?? null,
      requirements: body.requirements || [],
    });

    const session = await ResearchSession.create({
      projectId: project._id,
      userId: toObjectId(req.userId!, "userId"),
      query: body.query,
      status: started.status || "started",
      currentStage: "queued",
      progress: 0,
      fastApiResearchId: started.research_id,
      options: {
        depth: body.depth,
        mockMode: body.mockMode,
      },
    });

    res.status(202).json({
      research: serializeSession(session),
    });
  } catch (err) {
    next(err);
  }
}

export async function listResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const { projectId, status, page, limit } = req.query as unknown as {
      projectId?: string;
      status?: string;
      page: number;
      limit: number;
    };
    const filter: Record<string, unknown> = { userId: req.userId };
    if (projectId) filter.projectId = projectId;
    if (status) filter.status = status;

    const skip = (page - 1) * limit;
    const [items, total] = await Promise.all([
      ResearchSession.find(filter)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .select("-report -sources -claims -contradictions -analysis -charts -evidence"),
      ResearchSession.countDocuments(filter),
    ]);

    res.json({
      items: items.map((s) => serializeSession(s)),
      page,
      limit,
      total,
    });
  } catch (err) {
    next(err);
  }
}

export async function getResearchStatus(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    let session = await ownedSession(req.userId!, req.params.id);
    if (session.status !== "completed" && session.status !== "failed") {
      session = await syncFromFastApi(session);
    }
    res.json({
      researchId: String(session._id),
      fastApiResearchId: session.fastApiResearchId,
      status: session.status,
      currentStage: session.currentStage,
      progress: session.progress,
      error: session.error,
    });
  } catch (err) {
    next(err);
  }
}

export async function getResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    let session = await ownedSession(req.userId!, req.params.id);
    if (session.status !== "completed" && session.status !== "failed") {
      session = await syncFromFastApi(session);
    } else if (session.status === "completed" && !session.report) {
      session = await syncFromFastApi(session);
    }
    res.json({ research: serializeSession(session, { includePayload: true }) });
  } catch (err) {
    next(err);
  }
}

export async function getResearchSources(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const session = await ownedSession(req.userId!, req.params.id);
    if (session.sources?.length) {
      res.json({ items: session.sources });
      return;
    }
    const items = await fastApiService.getSources(session.fastApiResearchId);
    res.json({ items });
  } catch (err) {
    next(err);
  }
}

export async function getResearchClaims(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const session = await ownedSession(req.userId!, req.params.id);
    if (session.claims?.length) {
      res.json({ items: session.claims });
      return;
    }
    const items = await fastApiService.getClaims(session.fastApiResearchId);
    res.json({ items });
  } catch (err) {
    next(err);
  }
}

export async function getResearchReport(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    let session = await ownedSession(req.userId!, req.params.id);
    if (!session.report) {
      session = await syncFromFastApi(session);
    }
    if (session.report) {
      res.json({ report: session.report });
      return;
    }
    const report = await fastApiService.getReport(session.fastApiResearchId);
    res.json({ report });
  } catch (err) {
    next(err);
  }
}

export async function saveResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const session = await ownedSession(req.userId!, req.params.id);
    if (session.status !== "completed") {
      throw new AppError("RESEARCH_NOT_READY", "Only completed research can be saved", 409);
    }
    const title =
      (session.report as { title?: string } | null)?.title ||
      session.query.slice(0, 120);

    const saved = await SavedReport.findOneAndUpdate(
      { userId: req.userId, researchSessionId: session._id },
      {
        $setOnInsert: {
          userId: req.userId,
          researchSessionId: session._id,
          projectId: session.projectId,
          title,
          query: session.query,
        },
      },
      { upsert: true, new: true }
    );

    res.status(201).json({
      savedReport: {
        id: String(saved._id),
        researchSessionId: String(saved.researchSessionId),
        projectId: String(saved.projectId),
        title: saved.title,
        query: saved.query,
        createdAt: saved.createdAt,
      },
    });
  } catch (err) {
    next(err);
  }
}

export async function unsaveResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const result = await SavedReport.findOneAndDelete({
      userId: req.userId,
      researchSessionId: req.params.id,
    });
    if (!result) {
      throw new AppError("SAVED_REPORT_NOT_FOUND", "Saved report not found", 404);
    }
    res.json({ deleted: true });
  } catch (err) {
    next(err);
  }
}
