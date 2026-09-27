import mongoose from "mongoose";
import { env } from "./env";

export async function connectMongo(uri = env.MONGODB_URI): Promise<typeof mongoose> {
  mongoose.set("strictQuery", true);
  await mongoose.connect(uri);
  return mongoose;
}

export async function disconnectMongo(): Promise<void> {
  await mongoose.disconnect();
}
