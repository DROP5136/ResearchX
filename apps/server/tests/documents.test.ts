import fs from "fs";
import os from "os";
import path from "path";
import request from "supertest";
import { createApp } from "../src/app";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";

// Mock FastAPI document + research calls
jest.mock("../src/services/fastApiService", () => ({
  fastApiService: {
    processDocument: jest.fn(async () => ({
      document_id: "x",
      status: "ready",
      page_count: 2,
      chunk_count: 3,
      skipped_reembed: false,
      stage: "completed",
    })),
    deleteDocument: jest.fn(async () => ({ deleted_chunks: 3 })),
    startResearch: jest.fn(async () => ({ research_id: "RES_TEST", status: "started" })),
    getResearchStatus: jest.fn(),
    getResearchResult: jest.fn(),
    getSources: jest.fn(),
    getClaims: jest.fn(),
    getReport: jest.fn(),
    getLatestEvaluation: jest.fn(),
    runEvaluation: jest.fn(),
    health: jest.fn(),
  },
}));

const app = createApp();

function pdfBuffer(): Buffer {
  // Minimal PDF header + body accepted by our magic-byte check and stored as-is
  return Buffer.from("%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n", "utf8");
}

describe("documents", () => {
  let token: string;
  let projectId: string;

  beforeAll(async () => {
    process.env.DOCUMENTS_PATH = path.join(os.tmpdir(), `rx-docs-${Date.now()}`);
    fs.mkdirSync(process.env.DOCUMENTS_PATH, { recursive: true });
    await setupTestDb();
  });

  afterAll(async () => {
    await teardownTestDb();
  });

  beforeEach(async () => {
    await clearDb();
    const email = `doc${Date.now()}@example.com`;
    const reg = await request(app).post("/api/v1/auth/register").send({
      name: "Doc User",
      email,
      password: "password123",
    });
    token = reg.body.token;
    const proj = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "Docs Project" });
    projectId = proj.body.project.id;
  });

  it("uploads a PDF and lists it", async () => {
    const upload = await request(app)
      .post(`/api/v1/projects/${projectId}/documents`)
      .set("Authorization", `Bearer ${token}`)
      .attach("files", pdfBuffer(), "report.pdf");

    expect(upload.status).toBe(202);
    expect(upload.body.documentId).toBeTruthy();
    expect(upload.body.status).toBe("processing");

    // Allow async processDocumentAsync to finish
    await new Promise((r) => setTimeout(r, 100));

    const list = await request(app)
      .get(`/api/v1/projects/${projectId}/documents`)
      .set("Authorization", `Bearer ${token}`);
    expect(list.status).toBe(200);
    expect(list.body.items.length).toBe(1);
    expect(list.body.items[0].originalFilename).toBe("report.pdf");
  });

  it("rejects non-pdf content", async () => {
    const upload = await request(app)
      .post(`/api/v1/projects/${projectId}/documents`)
      .set("Authorization", `Bearer ${token}`)
      .attach("files", Buffer.from("not a pdf"), "note.pdf");
    expect(upload.status).toBe(400);
  });

  it("enforces project ownership on list", async () => {
    const other = await request(app).post("/api/v1/auth/register").send({
      name: "Other",
      email: `other${Date.now()}@example.com`,
      password: "password123",
    });
    const list = await request(app)
      .get(`/api/v1/projects/${projectId}/documents`)
      .set("Authorization", `Bearer ${other.body.token}`);
    expect(list.status).toBe(404);
  });

  it("deletes a document", async () => {
    const upload = await request(app)
      .post(`/api/v1/projects/${projectId}/documents`)
      .set("Authorization", `Bearer ${token}`)
      .attach("files", pdfBuffer(), "report.pdf");
    const id = upload.body.documentId as string;
    await new Promise((r) => setTimeout(r, 50));

    const del = await request(app)
      .delete(`/api/v1/documents/${id}`)
      .set("Authorization", `Bearer ${token}`);
    expect(del.status).toBe(200);
    expect(del.body.deleted).toBe(true);
  });
});
