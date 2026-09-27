import fs from "fs";
import path from "path";
import { env } from "../config/env";

/**
 * Local document storage abstraction.
 * Designed so a later S3 backend can replace these methods without changing controllers.
 */
export class LocalDocumentStorage {
  constructor(private readonly root = env.DOCUMENTS_PATH) {
    fs.mkdirSync(this.root, { recursive: true });
  }

  resolveKey(userId: string, projectId: string, filename: string): string {
    return path.join(userId, projectId, filename);
  }

  absolutePath(storageKey: string): string {
    const abs = path.resolve(this.root, storageKey);
    const root = path.resolve(this.root);
    if (!abs.startsWith(root + path.sep) && abs !== root) {
      throw new Error("Path traversal blocked");
    }
    return abs;
  }

  async ensureDir(storageKey: string): Promise<string> {
    const abs = this.absolutePath(storageKey);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    return abs;
  }

  async writeBuffer(storageKey: string, buffer: Buffer): Promise<string> {
    const abs = await this.ensureDir(storageKey);
    await fs.promises.writeFile(abs, buffer);
    return abs;
  }

  async delete(storageKey: string): Promise<void> {
    const abs = this.absolutePath(storageKey);
    try {
      await fs.promises.unlink(abs);
    } catch (err) {
      const code = (err as NodeJS.ErrnoException).code;
      if (code !== "ENOENT") throw err;
    }
  }

  async exists(storageKey: string): Promise<boolean> {
    try {
      await fs.promises.access(this.absolutePath(storageKey));
      return true;
    } catch {
      return false;
    }
  }
}

export const documentStorage = new LocalDocumentStorage();
