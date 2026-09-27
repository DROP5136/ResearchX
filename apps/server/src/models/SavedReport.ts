import { Schema, model, models, type InferSchemaType, type Types } from "mongoose";

const savedReportSchema = new Schema(
  {
    userId: { type: Schema.Types.ObjectId, ref: "User", required: true, index: true },
    researchSessionId: {
      type: Schema.Types.ObjectId,
      ref: "ResearchSession",
      required: true,
      index: true,
    },
    projectId: { type: Schema.Types.ObjectId, ref: "Project", required: true },
    title: { type: String, default: "", maxlength: 300 },
    query: { type: String, default: "", maxlength: 2000 },
  },
  { timestamps: true }
);

savedReportSchema.index({ userId: 1, researchSessionId: 1 }, { unique: true });

export type SavedReportDocument = InferSchemaType<typeof savedReportSchema> & {
  _id: Types.ObjectId;
};

export const SavedReport = models.SavedReport || model("SavedReport", savedReportSchema);
