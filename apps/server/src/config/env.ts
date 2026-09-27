import path from "path";
import dotenv from "dotenv";
import { z } from "zod";

// Always load apps/server/.env regardless of process cwd
dotenv.config({ path: path.resolve(__dirname, "../../.env") });

// Monorepo root: apps/server/src/config → ../../../../
const REPO_ROOT = path.resolve(__dirname, "../../../../");

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(5000),
  MONGODB_URI: z.string().min(1, "MONGODB_URI is required"),
  JWT_SECRET: z.string().min(16, "JWT_SECRET must be at least 16 characters"),
  JWT_EXPIRES_IN: z.string().default("7d"),
  FASTAPI_URL: z.string().url().default("http://127.0.0.1:8000"),
  CORS_ORIGIN: z.string().default("http://localhost:5173"),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().int().positive().default(900_000),
  RATE_LIMIT_MAX: z.coerce.number().int().positive().default(200),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  DOCUMENTS_PATH: z
    .string()
    .default(path.join(REPO_ROOT, "data", "documents")),
  MAX_UPLOAD_BYTES: z.coerce.number().int().positive().default(20 * 1024 * 1024),
  MAX_DOCS_PER_PROJECT: z.coerce.number().int().positive().default(20),
});

export type Env = z.infer<typeof envSchema>;

function loadEnv(): Env {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid environment configuration: ${msg}`);
  }
  const data = parsed.data;
  // Resolve relative DOCUMENTS_PATH against repo root
  if (!path.isAbsolute(data.DOCUMENTS_PATH)) {
    data.DOCUMENTS_PATH = path.resolve(REPO_ROOT, data.DOCUMENTS_PATH);
  }
  return data;
}

export const env = loadEnv();

export function corsOriginList(): string[] {
  return env.CORS_ORIGIN.split(",").map((o) => o.trim()).filter(Boolean);
}
