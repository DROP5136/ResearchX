import { randomUUID } from "crypto";
import type { NextFunction, Request, Response } from "express";

export function requestIdMiddleware(req: Request, res: Response, next: NextFunction): void {
  const incoming = req.header("X-Request-Id");
  const id = (incoming && incoming.trim()) || randomUUID();
  (req as Request & { requestId?: string }).requestId = id;
  res.setHeader("X-Request-Id", id);
  next();
}
