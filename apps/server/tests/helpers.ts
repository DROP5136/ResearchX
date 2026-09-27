import { MongoMemoryServer } from "mongodb-memory-server";
import mongoose from "mongoose";
import { connectMongo, disconnectMongo } from "../src/config/db";

let mongo: MongoMemoryServer;

export async function setupTestDb(): Promise<void> {
  mongo = await MongoMemoryServer.create();
  process.env.MONGODB_URI = mongo.getUri();
  // Reconnect with memory URI
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
  }
  await connectMongo(mongo.getUri());
}

export async function teardownTestDb(): Promise<void> {
  await disconnectMongo();
  if (mongo) await mongo.stop();
}

export async function clearDb(): Promise<void> {
  const collections = mongoose.connection.collections;
  for (const key of Object.keys(collections)) {
    await collections[key].deleteMany({});
  }
}
