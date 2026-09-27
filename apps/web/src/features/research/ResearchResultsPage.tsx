import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bookmark, ExternalLink, Search } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { getResearch, saveResearch } from "@/features/research/api";
import type { ChartSpec, Claim, Contradiction, Source } from "@/types/api";
import { DynamicChart } from "@/features/research/components/charts/DynamicChart";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { cn, formatDate, stageLabel } from "@/lib/utils";

const TABS = ["Overview", "Report", "Sources", "Claims", "Conflicts", "Data", "Methodology"] as const;
type Tab = (typeof TABS)[number];

export function ResearchResultsPage() {
  const { id = "" } = useParams();
  const [tab, setTab] = useState<Tab>("Overview");
  const [sourceFilter, setSourceFilter] = useState("");
  const [highlightSource, setHighlightSource] = useState<string | null>(null);
  const qc = useQueryClient();

  const researchQ = useQuery({
    queryKey: ["research", id],
    queryFn: () => getResearch(id),
    enabled: Boolean(id),
  });

  const saveM = useMutation({
    mutationFn: () => saveResearch(id),
    onSuccess: async () => {
      toast.success("Report saved");
      await qc.invalidateQueries({ queryKey: ["saved-reports"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Save failed"),
  });

  if (researchQ.isLoading) return <LoadingState label="Loading research results…" />;
  if (researchQ.isError) return <ErrorState onRetry={() => void researchQ.refetch()} />;

  const research = researchQ.data!.research;
  if (research.status !== "completed" && research.status !== "failed") {
    return (
      <div className="rx-panel p-6">
        <p className="font-medium">This session is still running.</p>
        <Link className="rx-btn-primary mt-4 inline-flex" to={`/research/${id}/progress`}>Open progress</Link>
      </div>
    );
  }

  const sources = (research.sources || []) as Source[];
  const claims = (research.claims || []) as Claim[];
  const contradictions = (research.contradictions || []) as Contradiction[];
  const charts = collectCharts(research.charts, research.analysis, research.report);
  const report = research.report;

  const filteredSources = sources.filter((s) => {
    const blob = `${s.title} ${s.domain} ${s.url} ${s.source_type}`.toLowerCase();
    return blob.includes(sourceFilter.toLowerCase());
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">Results</p>
          <h1 className="mt-1 font-display text-3xl text-ink-950 dark:text-white">{report?.title || "Research report"}</h1>
          <p className="mt-2 text-ink-600 dark:text-ink-300">{research.query}</p>
          <p className="mt-2 text-xs text-ink-400">
            Status: {research.status} · Stage: {stageLabel(research.currentStage)} · {formatDate(research.completedAt || research.updatedAt)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="rx-btn-primary" disabled={saveM.isPending || research.status !== "completed"} onClick={() => saveM.mutate()}>
            <Bookmark className="h-4 w-4" /> Save Report
          </button>
          <button
            type="button"
            className="rx-btn-secondary"
            onClick={() => {
              void navigator.clipboard.writeText(report?.markdown || research.query);
              toast.success("Copied to clipboard");
            }}
          >
            Copy
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Research result tabs">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={cn(
              "whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition",
              tab === t ? "bg-accent text-white" : "bg-white/70 text-ink-600 hover:bg-ink-100 dark:bg-ink-900 dark:text-ink-300"
            )}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="rx-panel space-y-4 p-5">
            <h2 className="font-display text-xl">Executive summary</h2>
            <p className="leading-7 text-ink-700 dark:text-ink-200">{report?.executive_summary || "No executive summary available."}</p>
            <h3 className="font-display text-lg">Key findings</h3>
            {(report?.key_findings || []).length ? (
              <ul className="list-disc space-y-2 pl-5 text-ink-700 dark:text-ink-200">
                {report!.key_findings!.map((f) => <li key={f}>{f}</li>)}
              </ul>
            ) : (
              <p className="text-sm text-ink-500">No key findings returned.</p>
            )}
          </div>
          <div className="space-y-4">
            <StatGrid sources={sources.length} claims={claims.length} conflicts={contradictions.length} analysis={research.analysis?.length || 0} />
            {contradictions.length > 0 ? (
              <div className="rx-panel border-amber-300/50 p-4 dark:border-amber-700/40">
                <p className="font-semibold text-amber-700 dark:text-amber-300">{contradictions.length} contradiction(s) detected</p>
                <button type="button" className="mt-2 text-sm text-accent" onClick={() => setTab("Conflicts")}>Review conflicts</button>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {tab === "Report" && (
        <div className="rx-panel p-5 sm:p-8">
          {report?.markdown ? (
            <div className="rx-prose max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ href, children }) => {
                    const safe =
                      typeof href === "string" &&
                      /^(https?:|mailto:)/i.test(href);
                    if (!safe) {
                      return <span>{children}</span>;
                    }
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noreferrer noopener"
                        onClick={() => {
                          const match = String(children).match(/SRC_[a-zA-Z0-9]+/);
                          if (match) {
                            setHighlightSource(match[0]);
                            setTab("Sources");
                          }
                        }}
                      >
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {report.markdown}
              </ReactMarkdown>
            </div>
          ) : (
            <EmptyState title="No markdown report" description="No report markdown was returned for this run." />
          )}
        </div>
      )}

      {tab === "Sources" && (
        <SourcesTab
          sources={filteredSources}
          sourceFilter={sourceFilter}
          setSourceFilter={setSourceFilter}
          highlightSource={highlightSource}
          setHighlightSource={setHighlightSource}
          claims={claims}
        />
      )}

      {tab === "Claims" && (
        <div className="space-y-3">
          {claims.length === 0 ? <EmptyState title="No claims" /> : claims.map((c) => (
            <article key={c.claim_id} className="rx-panel p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={c.verification_status} />
                {c.confidence != null ? <span className="text-xs text-ink-500">confidence {(c.confidence * 100).toFixed(0)}%</span> : null}
              </div>
              <p className="mt-3 text-ink-800 dark:text-ink-100">{c.claim}</p>
              <div className="mt-3 grid gap-2 text-sm text-ink-500 sm:grid-cols-2">
                <p>Evidence: {(c.evidence_ids || []).join(", ") || "—"}</p>
                <p>Sources: {(c.source_ids || []).map((sid) => (
                  <button key={sid} type="button" className="mr-2 text-accent underline-offset-2 hover:underline" onClick={() => { setHighlightSource(sid); setTab("Sources"); }}>{sid}</button>
                ))}</p>
              </div>
              {c.notes ? <p className="mt-2 text-sm text-ink-500">{c.notes}</p> : null}
            </article>
          ))}
        </div>
      )}

      {tab === "Conflicts" && (
        <div className="space-y-3">
          {contradictions.length === 0 ? (
            <EmptyState title="No contradictions detected" description="That can mean agreement — or insufficient overlapping claims." />
          ) : contradictions.map((c, idx) => {
            const related = claims.filter((cl) => (c.claim_ids || []).includes(cl.claim_id));
            return (
              <article key={c.contradiction_id || idx} className="rx-panel border-amber-300/40 p-5 dark:border-amber-700/30">
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-amber-700 dark:text-amber-300">Contradiction · {c.status || "open"}</p>
                <p className="mt-2 text-ink-800 dark:text-ink-100">{c.description || "Conflicting claims detected."}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {related.map((cl) => (
                    <div key={cl.claim_id} className="rounded-xl bg-ink-50 p-3 text-sm dark:bg-ink-950/60">
                      <p className="font-medium">{cl.claim}</p>
                      <p className="mt-1 text-ink-500">{cl.verification_status} · {(cl.source_ids || []).join(", ")}</p>
                    </div>
                  ))}
                </div>
                {c.possible_explanation ? <p className="mt-3 text-sm text-ink-500">Explanation: {c.possible_explanation}</p> : null}
                {c.sources?.length ? <p className="mt-2 text-xs text-ink-400">Sources: {c.sources.join(", ")}</p> : null}
              </article>
            );
          })}
        </div>
      )}

      {tab === "Data" && (
        <div className="space-y-4">
          {(research.analysis || []).length ? (
            <div className="overflow-x-auto rx-panel">
              <table className="min-w-full text-sm">
                <thead className="bg-ink-50 text-left dark:bg-ink-800">
                  <tr>
                    <th className="px-4 py-3">Metric</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Result</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {research.analysis!.map((a, i) => (
                    <tr key={i} className="border-t border-ink-100 dark:border-ink-800">
                      <td className="px-4 py-3">{a.metric || "—"}</td>
                      <td className="px-4 py-3">{String(a.analysis_type || "—")}</td>
                      <td className="px-4 py-3 font-mono text-xs">{typeof a.result === "object" ? JSON.stringify(a.result) : String(a.result ?? "—")}</td>
                      <td className="px-4 py-3">{a.status || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No quantitative analysis" description="Enable analysis on the next run, or the query may lack numeric evidence." />
          )}
          <div className="grid gap-4 lg:grid-cols-2">
            {charts.map((c, i) => <DynamicChart key={i} chart={c} />)}
          </div>
        </div>
      )}

      {tab === "Methodology" && (
        <div className="rx-panel space-y-4 p-5">
          <Section title="Research question" body={research.query} />
          <Section title="Methodology" body={report?.methodology || "Not provided."} />
          <Section title="Limitations" body={(report?.limitations || []).join("\n") || "None listed."} />
          <Section title="Pipeline notes" body={`Stage: ${stageLabel(research.currentStage)}\nProgress: ${research.progress}%\nFastAPI id: ${research.fastApiResearchId}\nStatus note: ${report?.status_note || "—"}`} />
        </div>
      )}
    </div>
  );
}

function isDocumentSource(s: Source) {
  return (
    s.source_type === "pdf" ||
    s.domain === "local-pdf" ||
    s.metadata?.source_kind === "document" ||
    Boolean(s.metadata?.document_id)
  );
}

function SourcesTab({
  sources,
  sourceFilter,
  setSourceFilter,
  highlightSource,
  setHighlightSource,
  claims,
}: {
  sources: Source[];
  sourceFilter: string;
  setSourceFilter: (v: string) => void;
  highlightSource: string | null;
  setHighlightSource: (v: string | null) => void;
  claims: Claim[];
}) {
  const [panel, setPanel] = useState<Source | null>(null);
  const docs = sources.filter(isDocumentSource);
  const web = sources.filter((s) => !isDocumentSource(s));

  function renderCard(s: Source, kind: "web" | "document") {
    const supported = claims.filter((c) => (c.source_ids || []).includes(s.source_id));
    return (
      <article key={s.source_id} className={cn("rx-panel p-4", highlightSource === s.source_id && "ring-2 ring-accent/40")}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-400">
              {kind === "document" ? "Document" : "Web"}
            </p>
            <h3 className="mt-1 font-semibold">{s.title || s.source_id}</h3>
            {kind === "document" ? (
              <p className="mt-1 text-sm text-ink-500">
                {String(s.metadata?.filename || s.title || "PDF")}
                {s.metadata?.page != null ? ` · p. ${s.metadata.page}` : ""}
              </p>
            ) : (
              <p className="mt-1 text-sm text-ink-500">
                {s.domain || "unknown domain"} · {s.source_type || "source"} · {s.published_at || "n/d"}
              </p>
            )}
            <p className="mt-2 text-sm text-ink-600 dark:text-ink-300">{s.snippet}</p>
            {supported.length ? (
              <p className="mt-2 text-xs text-ink-500">Supports {supported.length} claim(s)</p>
            ) : null}
            <p className="mt-2 font-mono text-xs text-ink-400">
              {s.source_id}
              {s.relevance_score != null ? ` · relevance ${s.relevance_score.toFixed(2)}` : ""}
              {s.quality_score != null ? ` · quality ${s.quality_score.toFixed(2)}` : ""}
            </p>
          </div>
          <div className="flex gap-2">
            {kind === "document" ? (
              <button type="button" className="rx-btn-secondary" onClick={() => { setPanel(s); setHighlightSource(s.source_id); }}>
                View excerpt
              </button>
            ) : s.url ? (
              <a className="rx-btn-secondary" href={s.url} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" /> Open
              </a>
            ) : null}
          </div>
        </div>
      </article>
    );
  }

  return (
    <div className="space-y-6">
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
        <input className="rx-input pl-9" placeholder="Filter sources…" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} />
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-xl">Web Sources</h2>
        {web.length === 0 ? <EmptyState title="No web sources" /> : web.map((s) => renderCard(s, "web"))}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-xl">Documents</h2>
        {docs.length === 0 ? (
          <EmptyState title="No document sources" description="Enable uploaded documents on the next research run." />
        ) : (
          docs.map((s) => renderCard(s, "document"))
        )}
      </section>

      {panel ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="dialog" aria-modal="true">
          <div className="rx-panel max-h-[80vh] w-full max-w-lg overflow-y-auto p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Document citation</p>
                <h3 className="mt-1 font-display text-2xl">{String(panel.metadata?.filename || panel.title)}</h3>
                <p className="mt-1 text-sm text-ink-500">
                  {panel.metadata?.page != null ? `Page ${panel.metadata.page}` : "Page n/a"}
                  {panel.metadata?.citation ? ` · ${panel.metadata.citation}` : ""}
                </p>
              </div>
              <button type="button" className="rx-btn-secondary" onClick={() => setPanel(null)}>Close</button>
            </div>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink-700 dark:text-ink-200">
              {panel.snippet || panel.metadata?.citation || "No excerpt available."}
            </p>
            <p className="mt-3 font-mono text-xs text-ink-400">{panel.source_id}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function collectCharts(
  charts?: ChartSpec[],
  analysis?: Array<{ chart_data?: ChartSpec; chart?: ChartSpec }>,
  report?: { charts?: ChartSpec[]; chart_data?: ChartSpec[] } | null
) {
  const out: ChartSpec[] = [];
  for (const c of charts || []) out.push(c);
  for (const a of analysis || []) {
    if (a.chart_data) out.push(a.chart_data);
    if (a.chart) out.push(a.chart);
  }
  for (const c of report?.charts || []) out.push(c);
  for (const c of report?.chart_data || []) out.push(c);
  return out;
}

function StatGrid({ sources, claims, conflicts, analysis }: { sources: number; claims: number; conflicts: number; analysis: number }) {
  const items = [
    ["Sources", sources],
    ["Claims", claims],
    ["Conflicts", conflicts],
    ["Analyses", analysis],
  ] as const;
  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(([label, value]) => (
        <div key={label} className="rx-panel p-4">
          <p className="text-xs uppercase tracking-[0.08em] text-ink-500">{label}</p>
          <p className="mt-2 font-display text-2xl">{value}</p>
        </div>
      ))}
    </div>
  );
}

function StatusPill({ status }: { status?: string }) {
  const s = (status || "unverified").toLowerCase();
  const tone = s.includes("support") && !s.includes("un")
    ? "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200"
    : s.includes("conflict") || s.includes("contradict")
      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
      : s.includes("unsupport")
        ? "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200"
        : "bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-200";
  return <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", tone)}>{status || "unverified"}</span>;
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <section>
      <h2 className="font-display text-xl">{title}</h2>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink-600 dark:text-ink-300">{body}</p>
    </section>
  );
}
