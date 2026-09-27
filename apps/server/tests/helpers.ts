import { MongoMemoryServer } from "mongodb-memory-server";
import mongoose from "mongoose";
import { connectMongo, disconnectMongo } from "../src/config/db";

let mongo: MongoMemoryServer | null = null;
let usingMemory = false;

/**
 * Prefer TEST_MONGODB_URI / local Mongo when reachable.
 * Otherwise use mongodb-memory-server (downloads binary on first use).
 */
export async function setupTestDb(): Promise<void> {
  const preferMemory = ["1", "true", "yes"].includes(
    (process.env.USE_MEMORY_MONGO || "").toLowerCase()
  );
  const candidates = [
    process.env.TEST_MONGODB_URI,
    !preferMemory ? "mongodb://127.0.0.1:27017/researchx-jest" : "",
  ].filter(Boolean) as string[];

  for (const uri of candidates) {
    try {
      if (mongoose.connection.readyState !== 0) {
        await mongoose.disconnect();
      }
      await mongoose.connect(uri, { serverSelectionTimeoutMS: 1500 });
      process.env.MONGODB_URI = uri;
      usingMemory = false;
      return;
    } catch {
      try {
        await mongoose.disconnect();
      } catch {
        /* ignore */
      }
    }
  }

  mongo = await MongoMemoryServer.create();
  process.env.MONGODB_URI = mongo.getUri();
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
  }
  await connectMongo(mongo.getUri());
  usingMemory = true;
}

export async function teardownTestDb(): Promise<void> {
  await disconnectMongo();
  if (usingMemory && mongo) {
    await mongo.stop();
    mongo = null;
  }
}

export async function clearDb(): Promise<void> {
  const collections = mongoose.connection.collections;
  for (const key of Object.keys(collections)) {
    await collections[key].deleteMany({});
  }
}
