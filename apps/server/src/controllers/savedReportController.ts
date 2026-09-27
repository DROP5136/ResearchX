import type { Response, NextFunction } from "express";
import { SavedReport } from "../models/SavedReport";
import type { AuthRequest } from "../middleware/auth";

export async function listSavedReports(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const items = await SavedReport.find({ userId: req.userId })
      .sort({ createdAt: -1 })
      .populate("researchSessionId", "status progress query completedAt");

    res.json({
      items: items.map((s) => ({
        id: String(s._id),
        researchSessionId: String(s.researchSessionId?._id || s.researchSessionId),
        projectId: String(s.projectId),
        title: s.title,
        query: s.query,
        createdAt: s.createdAt,
        research: s.researchSessionId && typeof s.researchSessionId === "object"
          ? {
              status: (s.researchSessionId as { status?: string }).status,
              progress: (s.researchSessionId as { progress?: number }).progress,
              completedAt: (s.researchSessionId as { completedAt?: Date }).completedAt,
            }
          : undefined,
      })),
      total: items.length,
    });
  } catch (err) {
    next(err);
  }
}
