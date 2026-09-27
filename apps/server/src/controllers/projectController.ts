import type { Response, NextFunction } from "express";
import { Project } from "../models/Project";
import type { AuthRequest } from "../middleware/auth";
import { AppError } from "../utils/errors";
import { toObjectId } from "../utils/helpers";

function serializeProject(p: {
  _id: unknown;
  userId: unknown;
  name: string;
  description?: string;
  createdAt?: Date;
  updatedAt?: Date;
}) {
  return {
    id: String(p._id),
    userId: String(p.userId),
    name: p.name,
    description: p.description || "",
    createdAt: p.createdAt,
    updatedAt: p.updatedAt,
  };
}

export async function createProject(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const { name, description } = req.body as { name: string; description?: string };
    const project = await Project.create({
      userId: toObjectId(req.userId!, "userId"),
      name,
      description: description || "",
    });
    res.status(201).json({ project: serializeProject(project) });
  } catch (err) {
    next(err);
  }
}

export async function listProjects(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const projects = await Project.find({ userId: req.userId }).sort({ createdAt: -1 });
    res.json({ items: projects.map(serializeProject), total: projects.length });
  } catch (err) {
    next(err);
  }
}

export async function getProject(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const project = await Project.findOne({ _id: req.params.id, userId: req.userId });
    if (!project) {
      throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
    }
    res.json({ project: serializeProject(project) });
  } catch (err) {
    next(err);
  }
}

export async function updateProject(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const updates = req.body as { name?: string; description?: string };
    const project = await Project.findOneAndUpdate(
      { _id: req.params.id, userId: req.userId },
      { $set: updates },
      { new: true }
    );
    if (!project) {
      throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
    }
    res.json({ project: serializeProject(project) });
  } catch (err) {
    next(err);
  }
}

export async function deleteProject(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const project = await Project.findOneAndDelete({ _id: req.params.id, userId: req.userId });
    if (!project) {
      throw new AppError("PROJECT_NOT_FOUND", "Project not found", 404);
    }
    res.json({ deleted: true, id: String(project._id) });
  } catch (err) {
    next(err);
  }
}
