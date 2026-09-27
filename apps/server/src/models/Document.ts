import { Schema, model, models, type InferSchemaType, type Types } from "mongoose";

const documentSchema = new Schema(
  {
    projectId: { type: Schema.Types.ObjectId, ref: "Project", required: true, index: true },
    userId: { type: Schema.Types.ObjectId, ref: "User", required: true, index: true },
    filename: { type: String, required: true },
    originalFilename: { type: String, required: true },
    mimeType: { type: String, required: true },
    size: { type: Number, required: true },
    status: {
      type: String,
      enum: ["uploaded", "processing", "ready", "failed"],
      default: "uploaded",
      index: true,
    },
    stage: {
      type: String,
      enum: ["uploading", "parsing", "chunking", "embedding", "indexing", "completed", "failed"],
      default: "uploading",
    },
    progress: { type: Number, default: null },
    pageCount: { type: Number, default: null },
    chunkCount: { type: Number, default: null },
    embeddingStatus: {
      type: String,
      enum: ["pending", "processing", "ready", "failed", "skipped"],
      default: "pending",
    },
    storageKey: { type: String, required: true },
    absolutePath: { type: String, required: true },
    error: { type: String, default: null },
    uploadedAt: { type: Date, default: Date.now },
    processedAt: { type: Date, default: null },
  },
  { timestamps: true }
);

documentSchema.index({ projectId: 1, userId: 1, createdAt: -1 });

export type ProjectDocument = InferSchemaType<typeof documentSchema> & {
  _id: Types.ObjectId;
};

export const Document =
  models.Document || model("Document", documentSchema);
