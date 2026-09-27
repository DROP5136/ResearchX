import path from "path";
import dotenv from "dotenv";
import { z } from "zod";

const REPO_ROOT = path.resolve(__dirname, "../../../../");

// Load local .env files when present; platform env vars always win.
dotenv.config({ path: path.resolve(REPO_ROOT, ".env") });
dotenv.config({ path: path.resolve(__dirname, "../../.env") });

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(5000),
  HOST: z.string().default("0.0.0.0"),
  MONGODB_URI: z.string().min(1, "MONGODB_URI is required"),
  JWT_SECRET: z.string().min(16, "JWT_SECRET must be at least 16 characters"),
  JWT_EXPIRES_IN: z.string().default("7d"),
  FASTAPI_URL: z.string().min(1).default("http://127.0.0.1:8000"),
  AI_SERVICE_TOKEN: z.string().default(""),
  CORS_ORIGIN: z.string().default("http://localhost:5173"),
  REDIS_URL: z.string().default(""),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().int().positive().default(900_000),
  RATE_LIMIT_MAX: z.coerce.number().int().positive().default(200),
  AUTH_RATE_LIMIT_MAX: z.coerce.number().int().positive().default(20),
  RESEARCH_RATE_LIMIT_MAX: z.coerce.number().int().positive().default(30),
  UPLOAD_RATE_LIMIT_MAX: z.coerce.number().int().positive().default(40),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  DOCUMENTS_PATH: z.string().default(path.join(REPO_ROOT, "data", "documents")),
  MAX_UPLOAD_BYTES: z.coerce.number().int().positive().default(20 * 1024 * 1024),
  MAX_DOCS_PER_PROJECT: z.coerce.number().int().positive().default(20),
  ALLOW_MOCK_MODE: z
    .string()
    .optional()
    .transform((v) => {
      if (v === undefined || v === "") return undefined;
      return ["1", "true", "yes", "on"].includes(v.toLowerCase());
    }),
  ALLOW_EVALUATION: z
    .string()
    .optional()
    .transform((v) => {
      if (v === undefined || v === "") return undefined;
      return ["1", "true", "yes", "on"].includes(v.toLowerCase());
    }),
});

export type Env = z.infer<typeof envSchema>;

function loadEnv(): Env {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid environment configuration: ${msg}`);
  }
  const data = parsed.data;
  // Render fromService "host" is hostname-only; normalize to an absolute URL.
  const rawFastapi = (data.FASTAPI_URL || "").trim();
  if (rawFastapi && !/^https?:\/\//i.test(rawFastapi)) {
    data.FASTAPI_URL = `https://${rawFastapi.replace(/\/$/, "")}`;
  } else {
    data.FASTAPI_URL = rawFastapi.replace(/\/$/, "");
  }
  try {
    // eslint-disable-next-line no-new
    new URL(data.FASTAPI_URL);
  } catch {
    throw new Error(`FASTAPI_URL is not a valid URL: ${data.FASTAPI_URL}`);
  }
  if (!path.isAbsolute(data.DOCUMENTS_PATH)) {
    data.DOCUMENTS_PATH = path.resolve(REPO_ROOT, data.DOCUMENTS_PATH);
  }
  if (data.NODE_ENV === "production" && !data.AI_SERVICE_TOKEN) {
    throw new Error("AI_SERVICE_TOKEN is required when NODE_ENV=production");
  }
  if (data.NODE_ENV === "production" && data.JWT_SECRET.length < 24) {
    throw new Error("JWT_SECRET must be at least 24 characters in production");
  }
  return data;
}

export const env = loadEnv();

export function corsOriginList(): string[] {
  return env.CORS_ORIGIN.split(",").map((o) => o.trim()).filter(Boolean);
}

export function mockModeAllowed(): boolean {
  if (env.ALLOW_MOCK_MODE !== undefined) return env.ALLOW_MOCK_MODE;
  return env.NODE_ENV !== "production";
}

export function evaluationAllowed(): boolean {
  if (env.ALLOW_EVALUATION !== undefined) return env.ALLOW_EVALUATION;
  return env.NODE_ENV !== "production";
}
