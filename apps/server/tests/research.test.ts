import request from "supertest";
import { createApp } from "../src/app";
import * as fastApiModule from "../src/services/fastApiService";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";

const app = createApp();

beforeAll(async () => {
  await setupTestDb();
});

afterAll(async () => {
  await teardownTestDb();
});

beforeEach(async () => {
  await clearDb();
  jest.restoreAllMocks();
});

async function registerAndProject() {
  const reg = await request(app).post("/api/v1/auth/register").send({
    name: "Researcher",
    email: `r-${Date.now()}@example.com`,
    password: "password123",
  });
  const token = reg.body.token as string;
  const project = await request(app)
    .post("/api/v1/projects")
    .set("Authorization", `Bearer ${token}`)
    .send({ name: "Demo Project" });
  return { token, projectId: project.body.project.id as string };
}

describe("Research", () => {
  it("creates research via mocked FastAPI and returns status/result", async () => {
    const { token, projectId } = await registerAndProject();

    jest.spyOn(fastApiModule.fastApiService, "startResearch").mockResolvedValue({
      research_id: "RES_mock_123",
      status: "started",
    });
    jest.spyOn(fastApiModule.fastApiService, "getResearchStatus").mockResolvedValue({
      research_id: "RES_mock_123",
      status: "completed",
      current_stage: "completed",
      progress: 100,
      message: "done",
      errors: [],
    });
    jest.spyOn(fastApiModule.fastApiService, "getResearchResult").mockResolvedValue({
      research_id: "RES_mock_123",
      query: "Analyze the Indian EV market from 2022 to 2026",
      status: "completed",
      progress: 100,
      report: { title: "EV Report", executive_summary: "Summary", markdown: "# Report" },
      sources: [{ source_id: "SRC_1", title: "Source", url: "https://example.com" }],
      claims: [{ claim_id: "CLM_1", claim: "Sales grew" }],
      contradictions: [],
      analysis: [{ metric: "yoy", result: 20 }],
      charts: [],
      evidence: [],
      errors: [],
    });

    const started = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({
        projectId,
        query: "Analyze the Indian EV market from 2022 to 2026",
        mockMode: true,
        depth: "quick",
      });
    expect(started.status).toBe(202);
    expect(started.body.research.fastApiResearchId).toBe("RES_mock_123");
    const researchId = started.body.research.id as string;

    const status = await request(app)
      .get(`/api/v1/research/${researchId}/status`)
      .set("Authorization", `Bearer ${token}`);
    expect(status.status).toBe(200);
    expect(status.body.status).toBe("completed");
    expect(status.body.progress).toBe(100);

    const result = await request(app)
      .get(`/api/v1/research/${researchId}`)
      .set("Authorization", `Bearer ${token}`);
    expect(result.status).toBe(200);
    expect(result.body.research.report.title).toBe("EV Report");
    expect(result.body.research.sources).toHaveLength(1);

    const history = await request(app)
      .get("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .query({ projectId, page: 1, limit: 20 });
    expect(history.status).toBe(200);
    expect(history.body.total).toBe(1);

    const saved = await request(app)
      .post(`/api/v1/research/${researchId}/save`)
      .set("Authorization", `Bearer ${token}`);
    expect(saved.status).toBe(201);

    const savedList = await request(app)
      .get("/api/v1/saved-reports")
      .set("Authorization", `Bearer ${token}`);
    expect(savedList.status).toBe(200);
    expect(savedList.body.total).toBe(1);
  });

  it("enforces research ownership", async () => {
    const a = await registerAndProject();
    const b = await registerAndProject();

    jest.spyOn(fastApiModule.fastApiService, "startResearch").mockResolvedValue({
      research_id: "RES_own",
      status: "started",
    });

    const started = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${a.token}`)
      .send({ projectId: a.projectId, query: "Ownership test query here" });
    const id = started.body.research.id;

    const res = await request(app)
      .get(`/api/v1/research/${id}`)
      .set("Authorization", `Bearer ${b.token}`);
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("RESEARCH_NOT_FOUND");
  });

  it("validates empty research query", async () => {
    const { token, projectId } = await registerAndProject();
    const res = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({ projectId, query: "" });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });
});
