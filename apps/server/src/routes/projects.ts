import { Router } from "express";
import * as projectController from "../controllers/projectController";
import { requireAuth } from "../middleware/auth";
import { validate } from "../middleware/validate";
import { idParamSchema, projectCreateSchema, projectUpdateSchema } from "../utils/validators";

const router = Router();

router.use(requireAuth);

router.post("/", validate(projectCreateSchema), projectController.createProject);
router.get("/", projectController.listProjects);
router.get("/:id", validate(idParamSchema, "params"), projectController.getProject);
router.patch(
  "/:id",
  validate(idParamSchema, "params"),
  validate(projectUpdateSchema),
  projectController.updateProject
);
router.delete("/:id", validate(idParamSchema, "params"), projectController.deleteProject);

export default router;
