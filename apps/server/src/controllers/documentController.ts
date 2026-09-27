import type { Response, NextFunction } from "express";
import { randomUUID } from "crypto";
import path from "path";
import { Document } from "../models/Document";
import { Project } from "../models/Project";
import type { AuthRequest } from "../middleware/auth";
import { documentStorage } from "../services/documentStorage";
import { fastApiService } from "../services/fastApiService";
import { env } from "../config/env";
import { AppError } from "../utils/errors";
import { toObjectId } from "../utils/helpers";

function serializeDoc(d: InstanceType<typeof Document>) {
  return {
    id: String(d._id),
    documentId: String(d._id),
    projectId: String(d.projectId),
    userId: String(d.userId),
    filename: d.originalFilename,
    originalFilename: d.originalFilename,
    mimeType: d.mimeType,
    size: d.size,
    status: d.status,
    stage: d.stage,
    progress: d.progress,
    pageCount: d.pageCount,
    chunkCount: d.chunkCount,
    embeddingStatus: d.embeddingStatus,
    error: d.error,
    uploadedAt: d.uploadedAt,
    processedAt: d.processedAt,
    createdAt: d.createdAt,
    updatedAt: d.updatedAt,
  };
}

function isPdfBuffer(buf: Buffer): boolean {
  return buf.length >= 5 && buf.subarray(0, 5).toString("utf8") === "%PDF-";
}

function safeFilename(original: string): string {
  const base = path.basename(original || "document.pdf").replace(/[^\w.\-()+ ]+/g, "_");
  const stem = base.replace(/\.pdf$/i, "").slice(0, 80) || "document";
  return `${stem}-${randomUUID().slice(0, 8)}.pdf`;
}

async function ownedProject(userId: string, projectId: string) {
  const project = await Project.findOne({ _id: projectId, userId });
  if (!project) throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
  return project;
}

async function ownedDocument(userId: string, documentId: string) {
  const doc = await Document.findOne({ _id: documentId, userId });
  if (!doc) throw new AppError("DOCUMENT_NOT_FOUND", "Document not found", 404);
  return doc;
}

async function processDocumentAsync(documentId: string): Promise<void> {
  const doc = await Document.findById(documentId);
  if (!doc) return;
  try {
    doc.status = "processing";
    doc.stage = "parsing";
    doc.progress = null;
    doc.embeddingStatus = "processing";
    doc.error = null;
    await doc.save();

    const result = await fastApiService.processDocument({
      path: doc.absolutePath,
      document_id: String(doc._id),
      original_filename: doc.originalFilename,
      force: false,
    });

    doc.status = "ready";
    doc.stage = "completed";
    doc.progress = 100;
    doc.pageCount = result.page_count;
    doc.chunkCount = result.chunk_count;
    doc.embeddingStatus = result.skipped_reembed ? "skipped" : "ready";
    doc.processedAt = new Date();
    doc.error = null;
    await doc.save();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Document processing failed";
    doc.status = "failed";
    doc.stage = "failed";
    doc.progress = null;
    doc.embeddingStatus = "failed";
    doc.error = message.slice(0, 500);
    await doc.save();
  }
}

export async function uploadDocuments(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const projectId = req.params.projectId;
    await ownedProject(req.userId!, projectId);

    const files = (req.files as Express.Multer.File[] | undefined) || [];
    if (!files.length) {
      throw new AppError("NO_FILES", "At least one PDF file is required", 400);
    }
    if (files.length > 5) {
      throw new AppError("TOO_MANY_FILES", "Upload at most 5 files per request", 400);
    }

    const existingCount = await Document.countDocuments({ projectId, userId: req.userId });
    if (existingCount + files.length > env.MAX_DOCS_PER_PROJECT) {
      throw new AppError(
        "DOCUMENT_LIMIT",
        `Project may have at most ${env.MAX_DOCS_PER_PROJECT} documents`,
        400
      );
    }

    const created = [];
    for (const file of files) {
      if (!isPdfBuffer(file.buffer)) {
        throw new AppError("INVALID_PDF", `File "${file.originalname}" is not a valid PDF`, 400);
      }
      const mimeOk =
        file.mimetype === "application/pdf" ||
        file.mimetype === "application/x-pdf" ||
        file.mimetype === "application/octet-stream";
      if (!mimeOk && !file.originalname.toLowerCase().endsWith(".pdf")) {
        throw new AppError("INVALID_MIME", `Unsupported MIME type for "${file.originalname}"`, 400);
      }
      if (file.size > env.MAX_UPLOAD_BYTES) {
        throw new AppError("FILE_TOO_LARGE", `File exceeds ${env.MAX_UPLOAD_BYTES} bytes`, 400);
      }

      const internalName = safeFilename(file.originalname);
      const storageKey = documentStorage.resolveKey(req.userId!, projectId, internalName);
      const absolutePath = await documentStorage.writeBuffer(storageKey, file.buffer);

      const doc = await Document.create({
        projectId: toObjectId(projectId, "projectId"),
        userId: toObjectId(req.userId!, "userId"),
        filename: internalName,
        originalFilename: path.basename(file.originalname).slice(0, 255),
        mimeType: "application/pdf",
        size: file.size,
        status: "uploaded",
        stage: "uploading",
        progress: 0,
        storageKey,
        absolutePath,
        embeddingStatus: "pending",
        uploadedAt: new Date(),
      });

      // Fire-and-forget processing
      void processDocumentAsync(String(doc._id));

      created.push({
        documentId: String(doc._id),
        status: "processing",
        filename: doc.originalFilename,
      });
    }

    // Mark as processing immediately for UX
    await Document.updateMany(
      { _id: { $in: created.map((c) => c.documentId) }, userId: req.userId },
      { $set: { status: "processing", stage: "parsing" } }
    );

    res.status(202).json({
      items: created,
      documentId: created[0]?.documentId,
      status: "processing",
    });
  } catch (err) {
    next(err);
  }
}

export async function listDocuments(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const projectId = req.params.projectId;
    await ownedProject(req.userId!, projectId);
    const items = await Document.find({ projectId, userId: req.userId }).sort({ createdAt: -1 });
    res.json({ items: items.map(serializeDoc) });
  } catch (err) {
    next(err);
  }
}

export async function getDocumentStatus(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const doc = await ownedDocument(req.userId!, req.params.id);
    res.json({
      documentId: String(doc._id),
      status: doc.status,
      progress: doc.progress,
      stage: doc.stage,
      pageCount: doc.pageCount,
      chunkCount: doc.chunkCount,
      embeddingStatus: doc.embeddingStatus,
      error: doc.error,
    });
  } catch (err) {
    next(err);
  }
}

export async function retryDocument(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const doc = await ownedDocument(req.userId!, req.params.id);
    if (doc.status !== "failed" && doc.status !== "ready") {
      throw new AppError("DOCUMENT_BUSY", "Document is already processing", 409);
    }
    doc.status = "processing";
    doc.stage = "parsing";
    doc.progress = null;
    doc.error = null;
    await doc.save();
    void processDocumentAsync(String(doc._id));
    res.json({ documentId: String(doc._id), status: "processing" });
  } catch (err) {
    next(err);
  }
}

export async function deleteDocument(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const doc = await ownedDocument(req.userId!, req.params.id);
    await documentStorage.delete(doc.storageKey);
    try {
      await fastApiService.deleteDocument(String(doc._id));
    } catch {
      // ignore vector delete errors
    }
    await doc.deleteOne();
    res.json({ deleted: true });
  } catch (err) {
    next(err);
  }
}

export { processDocumentAsync };
