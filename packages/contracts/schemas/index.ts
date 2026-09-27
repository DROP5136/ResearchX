/** Shared lightweight schema enums / constants (TS). */

export type ResearchDepth = "quick" | "standard" | "deep";

export const RESEARCH_DEPTHS: ResearchDepth[] = ["quick", "standard", "deep"];

export type PipelineStage =
  | "planning"
  | "researching"
  | "extracting"
  | "fact_checking"
  | "analyzing"
  | "writing"
  | "completed"
  | "failed";
