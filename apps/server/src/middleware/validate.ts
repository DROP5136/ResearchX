import type { NextFunction, Request, Response } from "express";
import type { ZodSchema } from "zod";
import { AppError } from "../utils/errors";

type Source = "body" | "query" | "params";

export function validate(schema: ZodSchema, source: Source = "body") {
  return (req: Request, _res: Response, next: NextFunction): void => {
    const parsed = schema.safeParse(req[source]);
    if (!parsed.success) {
      next(
        new AppError("VALIDATION_ERROR", "Invalid request", 400, {
          issues: parsed.error.issues.map((i) => ({
            path: i.path.join("."),
            message: i.message,
          })),
        })
      );
      return;
    }
    if (source === "body") req.body = parsed.data;
    else if (source === "query") req.query = parsed.data as Request["query"];
    else req.params = parsed.data as Request["params"];
    next();
  };
}
