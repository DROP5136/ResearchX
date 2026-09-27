import { Router } from "express";
import * as documentController from "../controllers/documentController";
import { requireAuth } from "../middleware/auth";
import { uploadPdf } from "../middleware/upload";
import { validate } from "../middleware/validate";
import { idParamSchema, projectIdParamSchema } from "../utils/validators";

const router = Router({ mergeParams: true });

router.use(requireAuth);

router.post(
  "/",
  validate(projectIdParamSchema, "params"),
  (req, res, next) => {
    // multer + nested @types/express versions can disagree under npm workspaces
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
