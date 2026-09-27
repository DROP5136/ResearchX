import { z } from "zod";

export const objectIdSchema = z
  .string()
  .regex(/^[a-fA-F0-9]{24}$/, "Invalid ObjectId");

export const registerSchema = z.object({
  name: z.string().trim().min(1).max(100),
  email: z.string().trim().email().max(255),
  password: z.string().min(8).max(128),
});

export const loginSchema = z.object({
  email: z.string().trim().email().max(255),
  password: z.string().min(1).max(128),
});

export const projectCreateSchema = z.object({
  name: z.string().trim().min(1).max(120),
  description: z.string().trim().max(2000).optional().default(""),
});

export const projectUpdateSchema = z
  .object({
    name: z.string().trim().min(1).max(120).optional(),
    description: z.string().trim().max(2000).optional(),
  })
  .refine((v) => v.name !== undefined || v.description !== undefined, {
    message: "At least one field is required",
  });

export const idParamSchema = z.object({
  id: objectIdSchema,
});

export const projectIdParamSchema = z.object({
  projectId: objectIdSchema,
});

export const researchCreateSchema = z
  .object({
    projectId: objectIdSchema,
    query: z.string().trim().min(3).max(2000),
    depth: z.enum(["quick", "standard", "deep"]).optional().default("standard"),
    maxIterations: z.number().int().min(0).max(5).optional(),
    enableWebSearch: z.boolean().optional().default(true),
    enablePdfRag: z.boolean().optional().default(false),
    enableDocumentResearch: z.boolean().optional().default(false),
    enableAnalysis: z.boolean().optional().default(true),
    mockMode: z.boolean().optional(),
    requirements: z.array(z.string().max(500)).max(20).optional().default([]),
    documentIds: z.array(objectIdSchema).max(20).optional().default([]),
  })
  .refine((v) => v.enableWebSearch || v.enablePdfRag || v.enableDocumentResearch || (v.documentIds?.length ?? 0) > 0, {
    message: "Enable web research and/or document research",
  });

export const researchListQuerySchema = z.object({
  projectId: objectIdSchema.optional(),
  status: z.string().optional(),
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});
