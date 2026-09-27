import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { getLatestEvaluation, runEvaluation } from "@/features/evaluation/api";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { formatPct } from "@/lib/utils";

const METRIC_KEYS = [
  ["claim_support_rate", "Claim support"],
  ["citation_coverage", "Citation coverage"],
  ["citation_correctness", "Citation correctness"],
  ["hallucination_rate", "Hallucination (proxy)"],
  ["numerical_accuracy", "Numerical accuracy"],
  ["topic_coverage", "Research completeness"],
] as const;

export function EvaluationPage() {
  const qc = useQueryClient();
  const evalQ = useQuery({
    queryKey: ["evaluation", "latest"],
    queryFn: getLatestEvaluation,
    retry: false,
  });

  const runM = useMutation({
    mutationFn: () => runEvaluation({ mockMode: true, limit: 5 }),
    onSuccess: async () => {
      toast.success("Evaluation finished");
      await qc.invalidateQueries({ queryKey: ["evaluation"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Evaluation failed"),
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl text-ink-950 dark:text-white">Evaluation</h1>
          <p className="mt-1 text-sm text-ink-500">
            Metrics from the ResearchX evaluation suite via FastAPI (proxied by Express). Values are never invented in the UI.
          </p>
        </div>
        <button type="button" className="rx-btn-primary" disabled={runM.isPending} onClick={() => runM.mutate()}>
          <Play className="h-4 w-4" />
          {runM.isPending ? "Running…" : "Run mock evaluation"}
        </button>
      </div>

      {evalQ.isLoading ? <LoadingState /> : null}
      {evalQ.isError ? (
        <EmptyState
          title="No evaluation results yet"
          description="Run a mock evaluation to populate metrics, or ensure FastAPI evaluation results exist."
          action={
            <button type="button" className="rx-btn-secondary" onClick={() => runM.mutate()}>
              Run now
            </button>
          }
        />
      ) : null}

      {evalQ.data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {METRIC_KEYS.map(([key, label]) => (
              <div key={key} className="rx-panel p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">{label}</p>
                <p className="mt-3 font-display text-3xl">{formatPct(evalQ.data.overall?.[key])}</p>
              </div>
            ))}
            <div className="rx-panel p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">Avg execution time</p>
              <p className="mt-3 font-display text-3xl">
                {evalQ.data.performance?.avg_execution_time != null
                  ? `${evalQ.data.performance.avg_execution_time.toFixed(2)}s`
                  : "—"}
              </p>
            </div>
          </div>

          <div className="rx-panel overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead className="bg-ink-50 text-left dark:bg-ink-800">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Support</th>
                  <th className="px-4 py-3">Citation</th>
                  <th className="px-4 py-3">Hallucination</th>
                </tr>
              </thead>
              <tbody>
                {(evalQ.data.results || []).slice(0, 25).map((r) => {
                  const metrics = (r.metrics || {}) as Record<string, number>;
                  return (
                    <tr key={String(r.id)} className="border-t border-ink-100 dark:border-ink-800">
                      <td className="px-4 py-3 font-mono text-xs">{String(r.id)}</td>
                      <td className="px-4 py-3">{String(r.category || "—")}</td>
                      <td className="px-4 py-3">{formatPct(metrics.claim_support_rate)}</td>
                      <td className="px-4 py-3">{formatPct(metrics.citation_correctness)}</td>
                      <td className="px-4 py-3">{formatPct(metrics.hallucination_rate)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {(evalQ.data.failures || []).length > 0 ? (
            <div className="rx-panel p-5">
              <h2 className="font-display text-xl">Failure categories</h2>
              <ul className="mt-3 space-y-2 text-sm text-ink-600 dark:text-ink-300">
                {(evalQ.data.failures || []).slice(0, 20).map((f, i) => (
                  <li key={i}>
                    <span className="font-mono text-xs">{String(f.question_id || "")}</span> ·{" "}
                    {String(f.failure_type || "unknown")} — {String(f.actual_behavior || f.likely_cause || "")}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
