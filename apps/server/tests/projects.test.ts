import request from "supertest";
import { createApp } from "../src/app";
import { clearDb, setupTestDb, teardownTestDb } from "./helpers";

const app = createApp();

async function authPair() {
  const a = await request(app).post("/api/v1/auth/register").send({
    name: "User A",
    email: `a-${Date.now()}@example.com`,
    password: "password123",
  });
  const b = await request(app).post("/api/v1/auth/register").send({
    name: "User B",
    email: `b-${Date.now()}@example.com`,
    password: "password123",
  });
  return { tokenA: a.body.token as string, tokenB: b.body.token as string };
}

beforeAll(async () => {
  await setupTestDb();
});

afterAll(async () => {
  await teardownTestDb();
});

beforeEach(async () => {
  await clearDb();
});

describe("Projects", () => {
  it("creates, lists, updates, deletes a project", async () => {
    const { tokenA } = await authPair();

    const created = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ name: "EV Study", description: "India EV" });
    expect(created.status).toBe(201);
    const id = created.body.project.id as string;

    const listed = await request(app)
      .get("/api/v1/projects")
      .set("Authorization", `Bearer ${tokenA}`);
    expect(listed.status).toBe(200);
    expect(listed.body.total).toBe(1);

    const updated = await request(app)
      .patch(`/api/v1/projects/${id}`)
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ name: "EV Study 2" });
    expect(updated.status).toBe(200);
    expect(updated.body.project.name).toBe("EV Study 2");

    const deleted = await request(app)
      .delete(`/api/v1/projects/${id}`)
      .set("Authorization", `Bearer ${tokenA}`);
    expect(deleted.status).toBe(200);
  });

  it("blocks cross-user project access", async () => {
    const { tokenA, tokenB } = await authPair();
    const created = await request(app)
      .post("/api/v1/projects")
      .set("Authorization", `Bearer ${tokenA}`)
      .send({ name: "Private" });
    const id = created.body.project.id;

    const res = await request(app)
      .get(`/api/v1/projects/${id}`)
      .set("Authorization", `Bearer ${tokenB}`);
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("PROJECT_NOT_FOUND");
  });

  it("rejects invalid ObjectId", async () => {
    const { tokenA } = await authPair();
    const res = await request(app)
      .get("/api/v1/projects/not-an-id")
      .set("Authorization", `Bearer ${tokenA}`);
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });
});
