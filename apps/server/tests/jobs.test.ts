import request from "supertest";
import { createApp } from "../src/app";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";
import { cacheGet, cacheSet, _resetRedisForTests } from "../src/services/redis";

jest.mock("../src/services/fastApiService", () => ({
  fastApiService: {
    processDocument: jest.fn(),
    deleteDocument: jest.fn(),
    startResearch: jest.fn(async () => ({ research_id: "RES_JOB", status: "queued" })),
    getResearchStatus: jest.fn(async () => ({
      research_id: "RES_JOB",
      status: "running",
      current_stage: "planning",
      progress: 10,
      errors: [],
    })),
    getResearchResult: jest.fn(async () => ({
      report: { title: "T", markdown: "# T" },
      sources: [{ title: "S1" }],
      claims: [],
      contradictions: [],
      analysis: [],
      charts: [],
      evidence: [],
      errors: [],
    })),
    getSources: jest.fn(),
    getClaims: jest.fn(),
    getReport: jest.fn(),
    getLatestEvaluation: jest.fn(),
    runEvaluation: jest.fn(),
    health: jest.fn(),
    cancelResearch: jest.fn(async () => ({
      research_id: "RES_JOB",
      status: "cancelled",
      current_stage: "cancelled",
      progress: 0,
      errors: [],
    })),
  },
}));

const app = createApp();

describe("research jobs + redis optional + SSE", () => {
  let token: string;
  let projectId: string;

  beforeAll(async () => {
    await setupTestDb();
  });

  afterAll(async () => {
    await teardownTestDb();
  });

  beforeEach(async () => {
    await clearDb();
    _resetRedisForTests();
    const reg = await request(app).post("/api/v1/auth/register").send({
      name: "Job User",
      email: `job${Date.now()}@example.com`,
      password: "password123",
    });
    token = reg.body.token;
    const proj = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "P1", description: "d" });
    projectId = proj.body.project.id;
  });

  it("creates research as queued and returns 202", async () => {
    const res = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({ projectId, query: "What is ResearchX?", mockMode: true });
    expect(res.status).toBe(202);
    expect(res.body.research.status).toBe("queued");
    expect(res.body.research.id).toBeTruthy();
  });

  it("status endpoint syncs progress from FastAPI", async () => {
    const created = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({ projectId, query: "Status sync", mockMode: true });
    const id = created.body.research.id;

    const status = await request(app)
      .get(`/api/v1/research/${id}/status`)
      .set("Authorization", `Bearer ${token}`);
    expect(status.status).toBe(200);
    expect(status.body.status).toBe("running");
    expect(status.body.progress).toBe(10);
    expect(status.body.currentStage).toBe("planning");
  });

  it("SSE progress stream emits events then ends on completion", async () => {
    const { fastApiService } = jest.requireMock("../src/services/fastApiService") as {
      fastApiService: {
        getResearchStatus: jest.Mock;
        getResearchResult: jest.Mock;
      };
    };
    fastApiService.getResearchStatus
      .mockResolvedValueOnce({
        research_id: "RES_JOB",
        status: "running",
        current_stage: "writing",
        progress: 90,
        errors: [],
      })
      .mockResolvedValue({
        research_id: "RES_JOB",
        status: "completed",
        current_stage: "completed",
        progress: 100,
        errors: [],
      });

    const created = await request(app)
      .post("/api/v1/research")
      .set("Authorization", `Bearer ${token}`)
      .send({ projectId, query: "SSE test", mockMode: true });
    const id = created.body.research.id;

    const res = await request(app)
      .get(`/api/v1/research/${id}/events`)
      .set("Authorization", `Bearer ${token}`)
      .buffer(true)
      .parse((response, cb) => {
        const data: Buffer[] = [];
        response.on("data", (chunk: Buffer) => data.push(chunk));
        response.on("end", () => cb(null, Buffer.concat(data).toString("utf8")));
      });

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/event-stream/);
    const text = String(res.body);
    expect(text).toContain("event: progress");
    expect(text).toContain("event: done");
    expect(text).toContain("completed");
  }, 20000);

  it("redis cache helpers no-op when REDIS_URL unset", async () => {
    _resetRedisForTests();
    expect(await cacheSet("research:progress:x", { status: "running" })).toBe(false);
    expect(await cacheGet("research:progress:x")).toBeNull();
  });

  it("ready endpoint reports mongo and optional redis", async () => {
    const res = await request(app).get("/ready");
    expect([200, 503]).toContain(res.status);
    expect(res.body.checks.redis_optional).toBe(true);
  });
});
