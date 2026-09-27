import { Router } from "express";
import type { Request, Response, NextFunction } from "express";
import { requireAuth } from "../middleware/auth";
import { fastApiService } from "../services/fastApiService";

const router = Router();

router.use(requireAuth);

router.get("/latest", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const data = await fastApiService.getLatestEvaluation();
    res.json(data);
  } catch (err) {
    next(err);
  }
});

router.post("/run", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const body = (req.body || {}) as { mockMode?: boolean; limit?: number };
    const data = await fastApiService.runEvaluation({
      mock_mode: body.mockMode ?? true,
      limit: body.limit,
    });
    res.json(data);
  } catch (err) {
    next(err);
  }
});

export default router;
