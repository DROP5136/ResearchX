import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { getResearch, getResearchStatus } from "@/features/research/api";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { cn, stageLabel } from "@/lib/utils";

const PIPELINE = [
  { key: "planning", label: "Planning", desc: "Decompose the question into research subtasks" },
  { key: "researching", label: "Researching", desc: "Search and retrieve candidate sources" },
  { key: "extracting_evidence", label: "Extracting Evidence", desc: "Pull claims with verbatim evidence spans" },
  { key: "fact_checking", label: "Fact Checking", desc: "Verify support and flag weak claims" },
  { key: "additional_research", label: "Additional Research", desc: "Iterate when evidence is insufficient" },
  { key: "analyzing", label: "Analysis", desc: "Compute deterministic quantitative metrics" },
  { key: "writing", label: "Writing", desc: "Compose the citation-grounded report" },
  { key: "completed", label: "Completed", desc: "Artifacts saved and ready to review" },
];

function stageIndex(stage?: string | null) {
  if (!stage) return 0;
  const s = stage.toLowerCase();
  if (s.includes("fail")) return -1;
  const idx = PIPELINE.findIndex((p) => s.includes(p.key) || p.key.includes(s));
  if (idx >= 0) return idx;
  if (s.includes("extract")) return 2;
  if (s.includes("fact")) return 3;
  if (s.includes("additional") || s.includes("need_more")) return 4;
  if (s.includes("analy")) return 5;
  if (s.includes("writ") || s.includes("report")) return 6;
  if (s.includes("complete") || s.includes("save")) return 7;
  if (s.includes("research") || s.includes("queued")) return 1;
  return 0;
}

export function ResearchProgressPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const statusQ = useQuery({
    queryKey: ["research-status", id],
    queryFn: () => getResearchStatus(id),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 2500;
    },
  });

  const detailQ = useQuery({
    queryKey: ["research", id],
    queryFn: () => getResearch(id),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const s = q.state.data?.research?.status;
      return s === "completed" || s === "failed" ? false : 5000;
    },
  });

  useEffect(() => {
    if (statusQ.data?.status === "completed") {
      navigate(`/research/${id}`, { replace: true });
    }
  }, [statusQ.data?.status, id, navigate]);

  if (statusQ.isLoading) return <LoadingState label="Connecting to research pipeline…" />;
  if (statusQ.isError) return <ErrorState message="Could not load research status." onRetry={() => void statusQ.refetch()} />;

  const status = statusQ.data!;
  const research = detailQ.data?.research;
  const currentIdx = stageIndex(status.currentStage);
  const failed = status.status === "failed";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">Live pipeline</p>
        <h1 className="mt-2 font-display text-3xl text-ink-950 dark:text-white">Research in progress</h1>
        <p className="mt-2 text-ink-600 dark:text-ink-300">{research?.query || "Loading question…"}</p>
      </div>

      <div className="rx-panel p-5">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium">{stageLabel(status.currentStage)}</span>
          <span className="font-mono text-ink-500">{status.progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
          <div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${Math.min(100, status.progress || 0)}%` }} />
        </div>
        {status.error ? <p className="mt-3 text-sm text-rose-600">{status.error}</p> : null}
      </div>

      <ol className="space-y-3">
        {PIPELINE.map((step, idx) => {
          const done = !failed && (status.status === "completed" || idx < currentIdx);
          const active = !failed && idx === currentIdx && status.status !== "completed";
          return (
            <li key={step.key} className={cn("rx-panel flex gap-4 p-4", active && "border-accent/40")}>
              <div className="mt-0.5">
                {done ? <CheckCircle2 className="h-5 w-5 text-accent" /> : active ? <Loader2 className="h-5 w-5 animate-spin text-accent" /> : <Circle className="h-5 w-5 text-ink-300" />}
              </div>
              <div>
                <p className="font-semibold">{step.label}</p>
                <p className="text-sm text-ink-500">{step.desc}</p>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Sources" value={research?.sources?.length ?? "—"} />
        <Metric label="Claims" value={research?.claims?.length ?? "—"} />
        <Metric label="Evidence" value={research?.evidence?.length ?? "—"} />
        <Metric label="Conflicts" value={research?.contradictions?.length ?? "—"} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rx-panel p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">{label}</p>
      <p className="mt-2 font-display text-2xl">{value}</p>
    </div>
  );
}
