import { Router } from "express";
import * as documentController from "../controllers/documentController";
import { requireAuth } from "../middleware/auth";
import { uploadLimiter } from "../middleware/rateLimits";
import { uploadPdf } from "../middleware/upload";
import { validate } from "../middleware/validate";
import { projectIdParamSchema } from "../utils/validators";

const router = Router({ mergeParams: true });

router.use(requireAuth);

router.post(
  "/",
  uploadLimiter,
  validate(projectIdParamSchema, "params"),
  (req, res, next) => {
    (uploadPdf as unknown as (r: typeof req, s: typeof res, n: (e?: unknown) => void) => void)(
      req,
      res,
      (err) => {
        if (err) return next(err);
        return documentController.uploadDocuments(req, res, next);
      }
    );
  }
);

router.get("/", validate(projectIdParamSchema, "params"), documentController.listDocuments);

export default router;
