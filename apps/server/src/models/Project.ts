import { Schema, model, models, type InferSchemaType, type Types } from "mongoose";

const projectSchema = new Schema(
  {
    userId: { type: Schema.Types.ObjectId, ref: "User", required: true, index: true },
    name: { type: String, required: true, trim: true, maxlength: 120 },
    description: { type: String, default: "", trim: true, maxlength: 2000 },
  },
  { timestamps: true }
);

projectSchema.index({ userId: 1, createdAt: -1 });

export type ProjectDocument = InferSchemaType<typeof projectSchema> & { _id: Types.ObjectId };

export const Project = models.Project || model("Project", projectSchema);
