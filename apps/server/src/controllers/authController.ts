import bcrypt from "bcryptjs";
import type { Response, NextFunction } from "express";
import { User } from "../models/User";
import type { AuthRequest } from "../middleware/auth";
import { AppError } from "../utils/errors";
import { signToken } from "../utils/jwt";
import { publicUser } from "../utils/helpers";

const SALT_ROUNDS = 12;

export async function register(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const { name, email, password } = req.body as {
      name: string;
      email: string;
      password: string;
    };

    const existing = await User.findOne({ email: email.toLowerCase() });
    if (existing) {
      throw new AppError("EMAIL_EXISTS", "An account with this email already exists", 409);
    }

    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);
    const user = await User.create({
      name,
      email: email.toLowerCase(),
      passwordHash,
    });

    const token = signToken({ sub: String(user._id), email: user.email });
    res.status(201).json({
      token,
      user: publicUser(user),
    });
  } catch (err) {
    next(err);
  }
}

export async function login(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const { email, password } = req.body as { email: string; password: string };
    const user = await User.findOne({ email: email.toLowerCase() }).select("+passwordHash");
    if (!user) {
      throw new AppError("INVALID_CREDENTIALS", "Invalid email or password", 401);
    }

    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) {
      throw new AppError("INVALID_CREDENTIALS", "Invalid email or password", 401);
    }

    const token = signToken({ sub: String(user._id), email: user.email });
    res.json({
      token,
      user: publicUser(user),
    });
  } catch (err) {
    next(err);
  }
}

export async function me(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
  try {
    const user = await User.findById(req.userId);
    if (!user) {
      throw new AppError("UNAUTHORIZED", "User not found", 401);
    }
    res.json({ user: publicUser(user) });
  } catch (err) {
    next(err);
  }
}
