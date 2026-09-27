import { Router } from "express";
import * as authController from "../controllers/authController";
import { requireAuth } from "../middleware/auth";
import { authLimiter } from "../middleware/rateLimits";
import { validate } from "../middleware/validate";
import { loginSchema, registerSchema } from "../utils/validators";

const router = Router();

router.post("/register", authLimiter, validate(registerSchema), authController.register);
router.post("/login", authLimiter, validate(loginSchema), authController.login);
router.get("/me", requireAuth, authController.me);

export default router;
