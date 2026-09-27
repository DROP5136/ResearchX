import type { Response, NextFunction } from "express";
import { Project } from "../models/Project";
import { ResearchSession } from "../models/ResearchSession";
import { SavedReport } from "../models/SavedReport";
import type { AuthRequest } from "../middleware/auth";
import { fastApiService } from "../services/fastApiService";
import { cacheGet, cacheSet } from "../services/redis";
import { mockModeAllowed } from "../config/env";
import { AppError } from "../utils/errors";
import { toObjectId } from "../utils/helpers";

/** Canonical job statuses for API responses (lowercase). */
export type ResearchStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

function normalizeStatus(status: string | undefined | null): ResearchStatus {
  const s = (status || "").toLowerCase();
  if (s === "cancelled" || s === "canceled") return "cancelled";
  if (s.includes("fail")) return "failed";
  if (s.includes("completed") || s.includes("insufficient")) return "completed";
  if (s === "started" || s === "queued") return "queued";
  if (s === "running" || s.includes("run")) return "running";
  return "running";
}

function serializeSession(
  s: {
    _id: unknown;
    projectId: unknown;
    userId: unknown;
    query: string;
    status: string;
    currentStage?: string | null;
    progress?: number;
    startedAt?: Date | null;
    completedAt?: Date | null;
    retryCount?: number;
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
  const status = normalizeStatus(s.status);
  const base = {
    id: String(s._id),
    projectId: String(s.projectId),
    userId: String(s.userId),
    query: s.query,
    status,
    currentStage: s.currentStage || null,
    progress: s.progress ?? 0,
    startedAt: s.startedAt || null,
    completedAt: s.completedAt || null,
    retryCount: s.retryCount ?? 0,
    fastApiResearchId: s.fastApiResearchId,
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

function progressCacheKey(sessionId: string) {
  return `research:progress:${sessionId}`;
}

async function syncFromFastApi(session: InstanceType<typeof ResearchSession>) {
  const status = await fastApiService.getResearchStatus(session.fastApiResearchId);
  const mapped = normalizeStatus(status.status);
  session.status = mapped;
  session.currentStage = status.current_stage || session.currentStage;
  session.progress = typeof status.progress === "number" ? status.progress : session.progress;
  if (status.errors?.length) {
    session.error = status.errors.join("; ");
  }
  if (mapped === "running" && !session.startedAt) {
    session.startedAt = new Date();
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

  await cacheSet(
    progressCacheKey(String(session._id)),
    {
      researchId: String(session._id),
      status: session.status,
      currentStage: session.currentStage,
      progress: session.progress,
      error: session.error,
      startedAt: session.startedAt,
      completedAt: session.completedAt,
    },
    120
  );

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
      enableDocumentResearch?: boolean;
      enableAnalysis?: boolean;
      mockMode?: boolean;
      requirements?: string[];
      documentIds?: string[];
    };

    const project = await Project.findOne({
      _id: body.projectId,
      userId: req.userId,
    });
    if (!project) {
      throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
    }

    const enableDocs =
      Boolean(body.enablePdfRag) ||
      Boolean(body.enableDocumentResearch) ||
      (body.documentIds?.length ?? 0) > 0;

    let pdfPaths: string[] = [];
    let documentIds: string[] = [];

    if (enableDocs && body.documentIds?.length) {
      const { Document } = await import("../models/Document");
      const docs = await Document.find({
        _id: { $in: body.documentIds },
        userId: req.userId,
        projectId: body.projectId,
      });
      if (docs.length !== body.documentIds.length) {
        throw new AppError("DOCUMENT_NOT_FOUND", "One or more documents were not found in this project", 404);
      }
      const notReady = docs.filter((d) => d.status !== "ready");
      if (notReady.length) {
        throw new AppError(
          "DOCUMENT_NOT_READY",
          `Documents still processing: ${notReady.map((d) => d.originalFilename).join(", ")}`,
          409
        );
      }
      pdfPaths = docs.map((d) => d.absolutePath);
      documentIds = docs.map((d) => String(d._id));
    }

    const started = await fastApiService.startResearch({
      query: body.query,
      depth: body.depth || "standard",
      max_iterations: body.maxIterations ?? null,
      enable_web_search: body.enableWebSearch ?? true,
      enable_pdf_rag: enableDocs,
      enable_document_research: enableDocs,
      enable_analysis: body.enableAnalysis ?? true,
      mock_mode: mockModeAllowed() ? (body.mockMode ?? null) : false,
      requirements: body.requirements || [],
      pdf_paths: pdfPaths,
      document_ids: documentIds,
    });

    const session = await ResearchSession.create({
      projectId: project._id,
      userId: toObjectId(req.userId!, "userId"),
      query: body.query,
      status: normalizeStatus(started.status || "queued"),
      currentStage: "queued",
      progress: 0,
      startedAt: null,
      retryCount: 0,
      fastApiResearchId: started.research_id,
      options: {
        depth: body.depth,
        mockMode: body.mockMode,
        documentIds,
        enableWebSearch: body.enableWebSearch,
        enableDocumentResearch: enableDocs,
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
    if (status) {
      const n = normalizeStatus(status);
      // Include legacy "started" when filtering queued
      filter.status = n === "queued" ? { $in: ["queued", "started"] } : n;
    }

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
    const terminal = ["completed", "failed", "cancelled"].includes(normalizeStatus(session.status));
    if (!terminal) {
      session = await syncFromFastApi(session);
    }
    const elapsedMs =
      session.startedAt != null ? Date.now() - new Date(session.startedAt).getTime() : null;
    res.json({
      researchId: String(session._id),
      fastApiResearchId: session.fastApiResearchId,
      status: normalizeStatus(session.status),
      currentStage: session.currentStage,
      progress: session.progress,
      error: session.error,
      startedAt: session.startedAt,
      completedAt: session.completedAt,
      elapsedMs,
      retryCount: session.retryCount ?? 0,
    });
  } catch (err) {
    next(err);
  }
}

export async function streamResearchEvents(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    let session = await ownedSession(req.userId!, req.params.id);

    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache, no-transform");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders?.();

    let closed = false;
    req.on("close", () => {
      closed = true;
    });

    const send = (event: string, data: unknown) => {
      if (closed) return;
      res.write(`event: ${event}\n`);
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    };

    send("connected", { researchId: String(session._id) });

    while (!closed) {
      const cached = await cacheGet<{
        status: string;
        currentStage?: string;
        progress?: number;
        error?: string | null;
      }>(progressCacheKey(String(session._id)));

      const terminal = ["completed", "failed", "cancelled"].includes(normalizeStatus(session.status));
      if (!terminal) {
        try {
          session = await syncFromFastApi(session);
        } catch (err) {
          send("error", {
            message: err instanceof Error ? err.message : "sync failed",
          });
        }
      } else if (cached) {
        /* already terminal — use DB state */
      }

      const status = normalizeStatus(session.status);
      const payload = {
        researchId: String(session._id),
        status,
        currentStage: session.currentStage,
        progress: session.progress ?? 0,
        error: session.error,
        startedAt: session.startedAt,
        completedAt: session.completedAt,
        elapsedMs:
          session.startedAt != null ? Date.now() - new Date(session.startedAt).getTime() : null,
      };
      send("progress", payload);

      if (status === "completed" || status === "failed" || status === "cancelled") {
        send("done", payload);
        break;
      }

      await new Promise((r) => setTimeout(r, 1500));
    }

    res.end();
  } catch (err) {
    next(err);
  }
}

export async function getResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    let session = await ownedSession(req.userId!, req.params.id);
    const status = normalizeStatus(session.status);
    if (status !== "completed" && status !== "failed" && status !== "cancelled") {
      session = await syncFromFastApi(session);
    } else if (status === "completed" && !session.report) {
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
    if (normalizeStatus(session.status) !== "completed") {
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

export async function cancelResearch(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const session = await ownedSession(req.userId!, req.params.id);
    const status = normalizeStatus(session.status);
    if (status === "completed" || status === "failed" || status === "cancelled") {
      res.json({ research: serializeSession(session) });
      return;
    }
    // Best-effort stop of FastAPI background job (Mongo remains source of truth for UI)
    try {
      await fastApiService.cancelResearch(session.fastApiResearchId);
    } catch {
      /* FastAPI may be briefly unavailable; still mark Mongo cancelled */
    }
    session.status = "cancelled";
    session.currentStage = "cancelled";
    session.completedAt = new Date();
    session.error = session.error || "Cancelled by user";
    await session.save();
    await cacheSet(
      progressCacheKey(String(session._id)),
      {
        researchId: String(session._id),
        status: "cancelled",
        currentStage: "cancelled",
        progress: session.progress,
        error: session.error,
      },
      120
    );
    res.json({ research: serializeSession(session) });
  } catch (err) {
    next(err);
  }
}
