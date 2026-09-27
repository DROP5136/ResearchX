import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { corsOriginList, env } from "./config/env";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler";
import authRoutes from "./routes/auth";
import projectRoutes from "./routes/projects";
import researchRoutes from "./routes/research";
import savedReportRoutes from "./routes/savedReports";
import evaluationRoutes from "./routes/evaluation";

export function createApp() {
  const app = express();

  app.set("trust proxy", 1);
  app.use(helmet());
  app.use(
    cors({
      origin: corsOriginList(),
      credentials: true,
    })
  );
  app.use(express.json({ limit: "1mb" }));
  app.use(
    rateLimit({
      windowMs: env.RATE_LIMIT_WINDOW_MS,
      max: env.RATE_LIMIT_MAX,
      standardHeaders: true,
      legacyHeaders: false,
      message: {
        error: { code: "RATE_LIMITED", message: "Too many requests" },
      },
    })
  );

  app.get("/health", (_req, res) => {
    res.json({
      status: "ok",
      service: "researchx-server",
      environment: env.NODE_ENV,
    });
  });

  app.use("/api/v1/auth", authRoutes);
  app.use("/api/v1/projects", projectRoutes);
  app.use("/api/v1/research", researchRoutes);
  app.use("/api/v1/saved-reports", savedReportRoutes);
  app.use("/api/v1/evaluation", evaluationRoutes);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
