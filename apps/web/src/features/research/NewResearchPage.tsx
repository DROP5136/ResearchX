import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { listProjects } from "@/features/projects/api";
import { listDocuments } from "@/features/projects/documentsApi";
import { startResearch } from "@/features/research/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

const EXAMPLES = [
  "Analyze the Indian EV market from 2022 to 2026 and compare Tata Motors, Mahindra and Hyundai.",
  "Compare the company's 2024 revenue in the uploaded annual report with industry growth online.",
  "What is the impact of AI on software engineering jobs?",
];

export function NewResearchPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const [projectId, setProjectId] = useState("");
  const [query, setQuery] = useState("");
  const [enableWeb, setEnableWeb] = useState(true);
  const [enablePdf, setEnablePdf] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [enableAnalysis, setEnableAnalysis] = useState(true);
  const [mockMode, setMockMode] = useState(true);
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");

  const projects = projectsQ.data?.items || [];
  const selected = projectId || projects[0]?.id || "";

  const docsQ = useQuery({
    queryKey: ["documents", selected],
    queryFn: () => listDocuments(selected),
    enabled: Boolean(selected) && enablePdf,
  });

  const readyDocs = useMemo(
    () => (docsQ.data?.items || []).filter((d) => d.status === "ready"),
    [docsQ.data]
  );

  useEffect(() => {
    if (!enablePdf) setSelectedDocs([]);
  }, [enablePdf]);

  const mutation = useMutation({
    mutationFn: startResearch,
    onSuccess: async (data) => {
      toast.success("Research started");
      await qc.invalidateQueries({ queryKey: ["research"] });
      navigate(`/research/${data.research.id}/progress`);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Failed to start research"),
  });

  if (projectsQ.isLoading) return <LoadingState />;
  if (projectsQ.isError) return <ErrorState onRetry={() => void projectsQ.refetch()} />;

  if (projects.length === 0) {
    return (
      <EmptyState
        title="Create a project first"
        description="Research sessions must belong to a project."
        action={<a className="rx-btn-primary" href="/projects">Go to Projects</a>}
      />
    );
  }

  function toggleDoc(id: string) {
    setSelectedDocs((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 3) {
      toast.error("Enter a research question (at least 3 characters)");
      return;
    }
    if (!enableWeb && !enablePdf) {
      toast.error("Enable web and/or uploaded documents");
      return;
    }
    if (enablePdf && selectedDocs.length === 0) {
      toast.error("Select at least one ready document, or turn off document research");
      return;
    }
    mutation.mutate({
      projectId: selected,
      query: q,
      depth,
      enableWebSearch: enableWeb,
      enablePdfRag: enablePdf,
      enableDocumentResearch: enablePdf,
      enableAnalysis,
      mockMode,
      documentIds: enablePdf ? selectedDocs : [],
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">New investigation</p>
        <h1 className="mt-2 font-display text-4xl leading-tight text-ink-950 dark:text-white">
          What do you want to research?
        </h1>
        <p className="mt-2 text-ink-500">
          Combine web sources and uploaded PDFs into a citation-grounded report.
        </p>
      </div>

      <form onSubmit={onSubmit} className="rx-panel space-y-5 p-6">
        <div>
          <label className="rx-label" htmlFor="query">Research question</label>
          <textarea
            id="query"
            className="rx-input min-h-[140px] resize-y font-display text-lg leading-relaxed"
            placeholder="Compare the company's 2024 revenue with industry growth."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={2000}
            required
          />
          <p className="mt-1 text-right text-xs text-ink-400">{query.length}/2000</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="rx-label" htmlFor="project">Project</label>
            <select id="project" className="rx-input" value={selected} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="rx-label" htmlFor="depth">Depth</label>
            <select id="depth" className="rx-input" value={depth} onChange={(e) => setDepth(e.target.value as typeof depth)}>
              <option value="quick">Quick</option>
              <option value="standard">Standard</option>
              <option value="deep">Deep</option>
            </select>
          </div>
        </div>

        <fieldset className="space-y-3">
          <legend className="rx-label">Research sources</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <Toggle label="Web" checked={enableWeb} onChange={setEnableWeb} />
            <Toggle label="Uploaded documents" checked={enablePdf} onChange={setEnablePdf} />
          </div>

          {enablePdf ? (
            <div className="rounded-xl border border-ink-200/80 p-4 dark:border-ink-700">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-ink-800 dark:text-ink-100">Document selector</p>
                <Link className="text-xs text-accent underline" to="/documents">Manage uploads</Link>
              </div>
              {docsQ.isLoading ? (
                <p className="text-sm text-ink-500">Loading documents…</p>
              ) : readyDocs.length === 0 ? (
                <p className="text-sm text-ink-500">
                  No ready PDFs in this project.{" "}
                  <Link className="text-accent underline" to="/documents">Upload documents</Link>
                </p>
              ) : (
                <ul className="space-y-2">
                  {readyDocs.map((d) => (
                    <li key={d.id}>
                      <label className="flex cursor-pointer items-start gap-3 text-sm">
                        <input
                          type="checkbox"
                          className="mt-0.5 h-4 w-4 accent-teal-700"
                          checked={selectedDocs.includes(d.id)}
                          onChange={() => toggleDoc(d.id)}
                        />
                        <span>
                          <span className="font-medium text-ink-900 dark:text-white">{d.originalFilename}</span>
                          <span className="block text-xs text-ink-500">
                            {d.pageCount != null ? `${d.pageCount} pages` : "Ready"}
                          </span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </fieldset>

        <fieldset className="grid gap-3 sm:grid-cols-2">
          <legend className="rx-label">Options</legend>
          <Toggle label="Enable quantitative analysis" checked={enableAnalysis} onChange={setEnableAnalysis} />
          <Toggle label="Mock mode (offline / no paid APIs)" checked={mockMode} onChange={setMockMode} />
        </fieldset>

        <button type="submit" className="rx-btn-primary w-full sm:w-auto" disabled={mutation.isPending}>
          {mutation.isPending ? "Starting…" : "Start Research"}
        </button>
      </form>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.08em] text-ink-500">Examples</h2>
        <div className="space-y-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="block w-full rounded-xl border border-ink-200/80 bg-white/60 px-4 py-3 text-left text-sm text-ink-700 transition hover:border-accent/40 dark:border-ink-700 dark:bg-ink-900/50 dark:text-ink-200"
              onClick={() => setQuery(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-ink-200/80 px-3 py-2.5 text-sm dark:border-ink-700">
      <input type="checkbox" className="h-4 w-4 accent-teal-700" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
