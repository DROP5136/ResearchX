import { Schema, model, models, type InferSchemaType, type Types } from "mongoose";

const researchSessionSchema = new Schema(
  {
    projectId: { type: Schema.Types.ObjectId, ref: "Project", required: true, index: true },
    userId: { type: Schema.Types.ObjectId, ref: "User", required: true, index: true },
    query: { type: String, required: true, maxlength: 2000 },
    status: {
      type: String,
      enum: ["queued", "running", "completed", "failed", "cancelled", "started"],
      default: "queued",
      index: true,
    },
    currentStage: { type: String, default: "queued" },
    progress: { type: Number, default: 0, min: 0, max: 100 },
    startedAt: { type: Date, default: null },
    completedAt: { type: Date, default: null },
    retryCount: { type: Number, default: 0, min: 0 },
    fastApiResearchId: { type: String, required: true, index: true },
    report: { type: Schema.Types.Mixed, default: null },
    sources: { type: [Schema.Types.Mixed], default: [] },
    claims: { type: [Schema.Types.Mixed], default: [] },
    contradictions: { type: [Schema.Types.Mixed], default: [] },
    analysis: { type: [Schema.Types.Mixed], default: [] },
    charts: { type: [Schema.Types.Mixed], default: [] },
    evidence: { type: [Schema.Types.Mixed], default: [] },
    error: { type: String, default: null },
    options: { type: Schema.Types.Mixed, default: {} },
  },
  { timestamps: true }
);

researchSessionSchema.index({ userId: 1, createdAt: -1 });
researchSessionSchema.index({ projectId: 1, createdAt: -1 });
researchSessionSchema.index({ userId: 1, status: 1, createdAt: -1 });
researchSessionSchema.index({ status: 1, updatedAt: -1 });

export type ResearchSessionDocument = InferSchemaType<typeof researchSessionSchema> & {
  _id: Types.ObjectId;
};

export const ResearchSession =
  models.ResearchSession || model("ResearchSession", researchSessionSchema);
