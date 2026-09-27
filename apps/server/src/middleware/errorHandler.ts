import type { NextFunction, Request, Response } from "express";
import { isAppError } from "../utils/errors";

export function notFoundHandler(_req: Request, res: Response): void {
  res.status(404).json({
    error: { code: "NOT_FOUND", message: "Route not found" },
  });
}

export function errorHandler(err: unknown, _req: Request, res: Response, _next: NextFunction): void {
  if (isAppError(err)) {
    res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message,
        ...(err.details ? { details: err.details } : {}),
      },
    });
    return;
  }

  // Mongoose duplicate key
  if (typeof err === "object" && err && "code" in err && (err as { code: number }).code === 11000) {
    res.status(409).json({
      error: { code: "DUPLICATE", message: "Resource already exists" },
    });
    return;
  }

  // Multer file size / unexpected field
  if (typeof err === "object" && err && "code" in err) {
    const code = String((err as { code: string }).code || "");
    if (code === "LIMIT_FILE_SIZE") {
      res.status(400).json({ error: { code: "FILE_TOO_LARGE", message: "Uploaded file is too large" } });
      return;
    }
    if (code === "LIMIT_FILE_COUNT" || code === "LIMIT_UNEXPECTED_FILE") {
      res.status(400).json({ error: { code: "UPLOAD_LIMIT", message: "Too many files or unexpected field" } });
      return;
    }
  }

  console.error("[researchx-server] Unhandled error:", err instanceof Error ? err.message : err);
  res.status(500).json({
    error: { code: "INTERNAL_ERROR", message: "An unexpected server error occurred" },
  });
}
