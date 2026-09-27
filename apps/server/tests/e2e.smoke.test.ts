/**
 * End-to-end smoke: auth → project → research → report (FastAPI mocked).
 */
import request from "supertest";
import { createApp } from "../src/app";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";

jest.mock("../src/services/fastApiService", () => ({
  fastApiService: {
    processDocument: jest.fn(),
    deleteDocument: jest.fn(),
    startResearch: jest.fn(async () => ({ research_id: "RES_SMOKE", status: "queued" })),
    getResearchStatus: jest
      .fn()
      .mockResolvedValueOnce({
        research_id: "RES_SMOKE",
        status: "running",
        current_stage: "planning",
        progress: 10,
        errors: [],
      })
      .mockResolvedValueOnce({
        research_id: "RES_SMOKE",
        status: "running",
        current_stage: "writing",
        progress: 90,
        errors: [],
      })
      .mockResolvedValue({
        research_id: "RES_SMOKE",
        status: "completed",
        current_stage: "completed",
        progress: 100,
        errors: [],
      }),
    getResearchResult: jest.fn(async () => ({
      research_id: "RES_SMOKE",
      query: "Smoke test EV market",
      status: "completed",
      progress: 100,
      report: {
        title: "Smoke Report",
        executive_summary: "Summary",
        markdown: "# Smoke Report",
        key_findings: ["Finding A"],
        references: [{ source_id: "SRC_1", title: "Source" }],
      },
      sources: [
        {
          source_id: "SRC_1",
          title: "Source",
          url: "https://example.com",
          source_type: "web",
        },
      ],
      evidence: [{ evidence_id: "EV_1", claim_id: "CLM_1", text: "Evidence text" }],
      claims: [
        {
          claim_id: "CLM_1",
          claim: "Sales grew 20%",
          verification_status: "supported",
          evidence_ids: ["EV_1"],
          source_ids: ["SRC_1"],
        },
      ],
      contradictions: [],
      analysis: [{ analysis_type: "yoy", status: "ok", value: 0.2 }],
      charts: [{ type: "bar", title: "YoY" }],
      errors: [],
    })),
    getSources: jest.fn(),
    getClaims: jest.fn(),
    getReport: jest.fn(),
    cancelResearch: jest.fn(async () => ({
      research_id: "RES_SMOKE",
      status: "cancelled",
      current_stage: "cancelled",
      progress: 10,
      errors: [],
    })),
    getLatestEvaluation: jest.fn(async () => ({ n: 0 })),
    runEvaluation: jest.fn(async () => ({ status: "completed" })),
    health: jest.fn(async () => ({ status: "ok" })),
  },
}));

const app = createApp();

describe("E2E smoke", () => {
  beforeAll(async () => {
    await setupTestDb();
  });

  afterAll(async () => {
    await teardownTestDb();
  });

  beforeEach(async () => {
    await clearDb();
  });

  it("completes mock research end-to-end", async () => {
    const health = await request(app).get("/health");
    expect(health.status).toBe(200);
    expect(health.body.status).toBe("ok");

    const email = `smoke${Date.now()}@example.com`;
    const reg = await request(app).post("/api/v1/auth/register").send({
      name: "Smoke User",
      email,
      password: "password123",
    });
    expect(reg.status).toBe(201);
    expect(reg.body.token).toBeTruthy();
    const token = reg.body.token as string;

    const login = await request(app).post("/api/v1/auth/login").send({
      email,
      password: "password123",
    });
    expect(login.status).toBe(200);
    expect(login.body.token).toBeTruthy();

    const project = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "Smoke Project", description: "e2e" });
    expect(project.status).toBe(201);
    const projectId = project.body.project.id as string;

    const started = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({
        projectId,
        query: "Smoke test EV market",
        mockMode: true,
        depth: "quick",
      });
    expect(started.status).toBe(202);
    expect(started.body.research.status).toBe("queued");
    expect(started.body.research.projectId).toBe(projectId);
    const researchId = started.body.research.id as string;

    const mid = await request(app)
      .get(`/api/v1/research/${researchId}/status`)
      .set("Authorization", `Bearer ${token}`);
    expect(mid.status).toBe(200);
    expect(["queued", "running", "completed"]).toContain(mid.body.status);

    const later = await request(app)
      .get(`/api/v1/research/${researchId}/status`)
      .set("Authorization", `Bearer ${token}`);
    expect(later.status).toBe(200);

    const result = await request(app)
      .get(`/api/v1/research/${researchId}`)
      .set("Authorization", `Bearer ${token}`);
    expect(result.status).toBe(200);
    const research = result.body.research;
    expect(research.id).toBe(researchId);
    expect(research.projectId).toBe(projectId);
    expect(research.status).toBe("completed");
    expect(research.report).toBeTruthy();
    expect(Array.isArray(research.sources)).toBe(true);
    expect(research.sources.length).toBeGreaterThan(0);
    expect(Array.isArray(research.claims)).toBe(true);
    expect(research.claims.length).toBeGreaterThan(0);
    expect(Array.isArray(research.evidence)).toBe(true);
    expect(Array.isArray(research.contradictions)).toBe(true);
    expect(Array.isArray(research.analysis)).toBe(true);
    expect(Array.isArray(research.charts)).toBe(true);

    const claim = research.claims[0];
    expect(claim.evidence_ids || claim.evidenceIds).toBeTruthy();

    const other = await request(app).post("/api/v1/auth/register").send({
      name: "Other",
      email: `other${Date.now()}@example.com`,
      password: "password123",
    });
    const denied = await request(app)
      .get(`/api/v1/research/${researchId}`)
      .set("Authorization", `Bearer ${other.body.token}`);
    expect(denied.status).toBe(404);

    const blob = JSON.stringify(result.body).toLowerCase();
    expect(blob).not.toContain("jwt_secret");
    expect(blob).not.toContain("passwordhash");
  });
});
