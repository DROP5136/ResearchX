import { Router } from "express";
import * as savedReportController from "../controllers/savedReportController";
import { requireAuth } from "../middleware/auth";

const router = Router();

router.use(requireAuth);
router.get("/", savedReportController.listSavedReports);

export default router;
