import request from "supertest";
import { createApp } from "../src/app";
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
});

describe("Auth", () => {
  it("registers a user", async () => {
    const res = await request(app).post("/api/v1/auth/register").send({
      name: "Lakshya",
      email: "lakshya@example.com",
      password: "password123",
    });
    expect(res.status).toBe(201);
    expect(res.body.token).toBeTruthy();
    expect(res.body.user.email).toBe("lakshya@example.com");
    expect(res.body.user.passwordHash).toBeUndefined();
  });

  it("rejects duplicate registration", async () => {
    const payload = {
      name: "Lakshya",
      email: "dup@example.com",
      password: "password123",
    };
    await request(app).post("/api/v1/auth/register").send(payload);
    const res = await request(app).post("/api/v1/auth/register").send(payload);
    expect(res.status).toBe(409);
    expect(res.body.error.code).toBe("EMAIL_EXISTS");
  });

  it("logs in with valid credentials", async () => {
    await request(app).post("/api/v1/auth/register").send({
      name: "A",
      email: "a@example.com",
      password: "password123",
    });
    const res = await request(app).post("/api/v1/auth/login").send({
      email: "a@example.com",
      password: "password123",
    });
    expect(res.status).toBe(200);
    expect(res.body.token).toBeTruthy();
  });

  it("rejects invalid password", async () => {
    await request(app).post("/api/v1/auth/register").send({
      name: "A",
      email: "b@example.com",
      password: "password123",
    });
    const res = await request(app).post("/api/v1/auth/login").send({
      email: "b@example.com",
      password: "wrong-password",
    });
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe("INVALID_CREDENTIALS");
  });

  it("returns /me for valid token", async () => {
    const reg = await request(app).post("/api/v1/auth/register").send({
      name: "Me",
      email: "me@example.com",
      password: "password123",
    });
    const res = await request(app)
      .get("/api/v1/auth/me")
      .set("Authorization", `Bearer ${reg.body.token}`);
    expect(res.status).toBe(200);
    expect(res.body.user.email).toBe("me@example.com");
  });

  it("rejects invalid token", async () => {
    const res = await request(app)
      .get("/api/v1/auth/me")
      .set("Authorization", "Bearer not-a-real-token");
    expect(res.status).toBe(401);
  });

  it("validates malformed register body", async () => {
    const res = await request(app).post("/api/v1/auth/register").send({
      name: "",
      email: "not-an-email",
      password: "short",
    });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });
});
