import { Types } from "mongoose";
import { AppError } from "./errors";

export function toObjectId(id: string, field = "id"): Types.ObjectId {
  if (!Types.ObjectId.isValid(id)) {
    throw new AppError("VALIDATION_ERROR", `Invalid ${field}`, 400, { field });
  }
  return new Types.ObjectId(id);
}

export function publicUser(user: { _id: unknown; name: string; email: string; createdAt?: Date; updatedAt?: Date }) {
  return {
    id: String(user._id),
    name: user.name,
    email: user.email,
    createdAt: user.createdAt,
    updatedAt: user.updatedAt,
  };
}
