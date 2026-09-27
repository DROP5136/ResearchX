import { Router } from "express";
import * as documentController from "../controllers/documentController";
import { requireAuth } from "../middleware/auth";
import { validate } from "../middleware/validate";
import { idParamSchema } from "../utils/validators";

const router = Router();

router.use(requireAuth);

router.get("/:id/status", validate(idParamSchema, "params"), documentController.getDocumentStatus);
router.post("/:id/retry", validate(idParamSchema, "params"), documentController.retryDocument);
router.delete("/:id", validate(idParamSchema, "params"), documentController.deleteDocument);

export default router;
