import { Router } from "express";
import * as researchController from "../controllers/researchController";
import { requireAuth } from "../middleware/auth";
import { validate } from "../middleware/validate";
import { idParamSchema, researchCreateSchema, researchListQuerySchema } from "../utils/validators";

const router = Router();

router.use(requireAuth);

router.post("/", validate(researchCreateSchema), researchController.startResearch);
router.get("/", validate(researchListQuerySchema, "query"), researchController.listResearch);
router.get("/:id", validate(idParamSchema, "params"), researchController.getResearch);
router.get("/:id/status", validate(idParamSchema, "params"), researchController.getResearchStatus);
router.get("/:id/sources", validate(idParamSchema, "params"), researchController.getResearchSources);
router.get("/:id/claims", validate(idParamSchema, "params"), researchController.getResearchClaims);
router.get("/:id/report", validate(idParamSchema, "params"), researchController.getResearchReport);
router.post("/:id/save", validate(idParamSchema, "params"), researchController.saveResearch);
router.delete("/:id/save", validate(idParamSchema, "params"), researchController.unsaveResearch);

export default router;
