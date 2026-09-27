import request from "supertest";
import { createApp } from "../src/app";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";
import { signToken } from "../src/utils/jwt";

jest.mock("../src/services/fastApiService", () => ({
  fastApiService: {
    processDocument: jest.fn(async () => ({
      document_id: "x",
      status: "ready",
      page_count: 1,
      chunk_count: 1,
      skipped_reembed: false,
      stage: "completed",
    })),
    deleteDocument: jest.fn(async () => ({ deleted_chunks: 0 })),
    startResearch: jest.fn(async () => ({ research_id: "RES_SEC", status: "started" })),
    getResearchStatus: jest.fn(),
    getResearchResult: jest.fn(),
    getSources: jest.fn(),
    getClaims: jest.fn(),
    getReport: jest.fn(),
    cancelResearch: jest.fn(async () => ({ research_id: "RES_SEC", status: "cancelled" })),
    getLatestEvaluation: jest.fn(async () => ({ n: 0 })),
    runEvaluation: jest.fn(async () => ({ status: "completed" })),
    health: jest.fn(),
  },
}));

const app = createApp();

describe("security", () => {
  let tokenA: string;
  let tokenB: string;
  let projectA: string;

  beforeAll(async () => {
    await setupTestDb();
  });

  afterAll(async () => {
    await teardownTestDb();
  });

  beforeEach(async () => {
    await clearDb();
    const a = await request(app).post("/api/v1/auth/register").send({
      name: "Alice",
      email: `alice${Date.now()}@example.com`,
      password: "password123",
    });
    tokenA = a.body.token;
    const b = await request(app).post("/api/v1/auth/register").send({
      name: "Bob",
      email: `bob${Date.now()}@example.com`,
      password: "password123",
    });
    tokenB = b.body.token;
    const proj = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ name: "Alice Project" });
    projectA = proj.body.project.id;
  });

  it("rejects missing auth on protected routes", async () => {
    const res = await request(app).get("/api/v1/projects");
    expect(res.status).toBe(401);
  });

  it("rejects malformed JWT", async () => {
    const res = await request(app)
      .get("/api/v1/projects")
      .set("Authorization", "Bearer not-a-jwt");
    expect(res.status).toBe(401);
  });

  it("rejects forged token with wrong secret payload shape via verify", async () => {
    // Token signed for a non-existent user should not expose Alice's project
    const forged = signToken({ sub: "000000000000000000000000", email: "forged@example.com" });
    const res = await request(app)
      .get(`/api/v1/projects/${projectA}`)
      .set("Authorization", `Bearer ${forged}`);
    expect(res.status).toBe(404);
  });

  it("blocks cross-user project access", async () => {
    const res = await request(app)
      .get(`/api/v1/projects/${projectA}`)
      .set("Authorization", `Bearer ${tokenB}`);
    expect(res.status).toBe(404);
  });

  it("rejects empty and oversized research queries", async () => {
    const empty = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ projectId: projectA, query: "ab" });
    expect(empty.status).toBe(400);

    const huge = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ projectId: projectA, query: "q".repeat(2001) });
    expect(huge.status).toBe(400);
  });

  it("rejects malformed ObjectIds", async () => {
    const res = await request(app)
      .get("/api/v1/projects/not-an-objectid")
      .set("Authorization", `Bearer ${tokenA}`);
    expect(res.status).toBe(400);
  });

  it("rejects path-traversal style filenames on upload", async () => {
    const pdf = Buffer.from("%PDF-1.4\n%%EOF\n", "utf8");
    const res = await request(app)
      .post(`/api/v1/projects/${projectA}/documents`)
      .set("Authorization", `Bearer ${tokenA}`)
      .attach("files", pdf, "../../etc/passwd.pdf");
    // Upload may succeed with sanitized basename; must not 500
    expect([202, 400]).toContain(res.status);
    if (res.status === 202) {
      expect(String(res.body.items?.[0]?.filename || "")).not.toContain("..");
    }
  });

  it("adds X-Request-Id header", async () => {
    const res = await request(app).get("/health");
    expect(res.headers["x-request-id"]).toBeTruthy();
  });

  it("does not leak stack traces on validation errors", async () => {
    const res = await request(app)
      .post("/api/v1/auth/register")
      .send({ name: "", email: "bad", password: "x" });
    expect(res.status).toBe(400);
    expect(res.body.error).toBeTruthy();
    expect(JSON.stringify(res.body)).not.toMatch(/at Object\./);
    expect(JSON.stringify(res.body)).not.toMatch(/node_modules/);
  });
});
