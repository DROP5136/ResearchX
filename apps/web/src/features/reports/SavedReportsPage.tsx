import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { unsaveResearch } from "@/features/research/api";
import { listSavedReports } from "@/features/reports/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDate } from "@/lib/utils";

export function SavedReportsPage() {
  const [q, setQ] = useState("");
  const qc = useQueryClient();
  const savedQ = useQuery({ queryKey: ["saved-reports"], queryFn: listSavedReports });

  const unsaveM = useMutation({
    mutationFn: (researchSessionId: string) => unsaveResearch(researchSessionId),
    onSuccess: async () => {
      toast.success("Removed from saved");
      await qc.invalidateQueries({ queryKey: ["saved-reports"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Remove failed"),
  });

  const filtered = useMemo(() => {
    const items = savedQ.data?.items || [];
    const needle = q.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((i) => `${i.title} ${i.query}`.toLowerCase().includes(needle));
  }, [savedQ.data, q]);

  if (savedQ.isLoading) return <LoadingState />;
  if (savedQ.isError) return <ErrorState onRetry={() => void savedQ.refetch()} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink-950 dark:text-white">Saved reports</h1>
        <p className="mt-1 text-sm text-ink-500">References to completed research sessions you bookmarked.</p>
      </div>

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
        <input className="rx-input pl-9" placeholder="Search saved reports…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No saved reports" description="Save a completed report from the results page." />
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <article key={item.id} className="rx-panel flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <Link to={`/research/${item.researchSessionId}`} className="font-semibold hover:text-accent">
                  {item.title || item.query}
                </Link>
                <p className="mt-1 line-clamp-2 text-sm text-ink-500">{item.query}</p>
                <p className="mt-2 text-xs text-ink-400">
                  Saved {formatDate(item.createdAt)} · project {item.projectId.slice(-6)}
                </p>
              </div>
              <div className="flex gap-2">
                <Link className="rx-btn-secondary" to={`/research/${item.researchSessionId}`}>Open</Link>
                <button type="button" className="rx-btn-ghost text-rose-600" onClick={() => unsaveM.mutate(item.researchSessionId)}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
