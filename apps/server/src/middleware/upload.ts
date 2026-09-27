import multer from "multer";
import { env } from "../config/env";
import { AppError } from "../utils/errors";

const storage = multer.memoryStorage();

export const uploadPdf = multer({
  storage,
  limits: {
    fileSize: env.MAX_UPLOAD_BYTES,
    files: 5,
  },
  fileFilter: (_req, file, cb) => {
    const name = (file.originalname || "").toLowerCase();
    const mime = (file.mimetype || "").toLowerCase();
    const okMime =
      mime === "application/pdf" ||
      mime === "application/x-pdf" ||
      mime === "application/octet-stream";
    if (!name.endsWith(".pdf") && !okMime) {
      cb(new AppError("INVALID_FILE_TYPE", "Only PDF uploads are allowed", 400));
      return;
    }
    cb(null, true);
  },
}).array("files", 5);
