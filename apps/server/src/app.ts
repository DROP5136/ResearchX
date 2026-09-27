import express from "express";
import cors from "cors";
import helmet from "helmet";
import mongoose from "mongoose";
import { corsOriginList, env } from "./config/env";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler";
import { globalLimiter } from "./middleware/rateLimits";
import { requestIdMiddleware } from "./middleware/requestId";
import { redisConfigured, redisPing, cacheStats } from "./services/redis";
import authRoutes from "./routes/auth";
import projectRoutes from "./routes/projects";
import projectDocumentRoutes from "./routes/projectDocuments";
import documentRoutes from "./routes/documents";
import researchRoutes from "./routes/research";
import savedReportRoutes from "./routes/savedReports";
import evaluationRoutes from "./routes/evaluation";

export function createApp() {
  const app = express();

  app.set("trust proxy", 1);
  app.use(requestIdMiddleware);
  app.use(
    helmet({
      contentSecurityPolicy: false, // API-only; frontend is separate origin
      crossOriginResourcePolicy: { policy: "cross-origin" },
    })
  );
  app.use(
    cors({
      origin: corsOriginList(),
      credentials: true,
    })
  );
  app.use(express.json({ limit: "1mb" }));
  app.use(globalLimiter);

  app.get("/health", (_req, res) => {
    res.json({
      status: "ok",
      service: "researchx-server",
      environment: env.NODE_ENV,
    });
  });

  app.get("/ready", async (_req, res) => {
    const mongoOk = mongoose.connection.readyState === 1;
    const redisOk = redisConfigured() ? await redisPing() : null;
    const ready = mongoOk;
    res.status(ready ? 200 : 503).json({
      status: ready ? "ready" : "not_ready",
      service: "researchx-server",
      checks: {
        mongodb: mongoOk,
        redis: redisOk,
        redis_optional: true,
        cache: cacheStats(),
      },
    });
  });

  app.use("/api/v1/auth", authRoutes);
  app.use("/api/v1/projects", projectRoutes);
  app.use("/api/v1/projects/:projectId/documents", projectDocumentRoutes);
  app.use("/api/v1/documents", documentRoutes);
  app.use("/api/v1/research", researchRoutes);
  app.use("/api/v1/saved-reports", savedReportRoutes);
  app.use("/api/v1/evaluation", evaluationRoutes);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
