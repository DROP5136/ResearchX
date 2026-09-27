import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { listProjects } from "@/features/projects/api";
import {
  deleteDocument,
  listDocuments,
  retryDocument,
  uploadDocuments,
  type ProjectDocument,
} from "@/features/projects/documentsApi";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDate } from "@/lib/utils";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(d: ProjectDocument) {
  if (d.status === "ready") return "Ready";
  if (d.status === "failed") return "Failed";
  if (d.status === "processing") return d.stage ? `Processing · ${d.stage}` : "Processing";
  return "Uploaded";
}

export function DocumentsPage() {
  const qc = useQueryClient();
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const [projectId, setProjectId] = useState("");
  const [dragging, setDragging] = useState(false);

  const projects = projectsQ.data?.items || [];
  const selected = projectId || projects[0]?.id || "";

  const docsQ = useQuery({
    queryKey: ["documents", selected],
    queryFn: () => listDocuments(selected),
    enabled: Boolean(selected),
    refetchInterval: (q) => {
      const items = q.state.data?.items || [];
      return items.some((d) => d.status === "processing" || d.status === "uploaded") ? 2000 : false;
    },
  });

  const uploadM = useMutation({
    mutationFn: (files: File[]) => uploadDocuments(selected, files),
    onSuccess: async () => {
      toast.success("Upload started — processing in background");
      await qc.invalidateQueries({ queryKey: ["documents", selected] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Upload failed"),
  });

  const deleteM = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      toast.success("Document removed");
      await qc.invalidateQueries({ queryKey: ["documents", selected] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Delete failed"),
  });

  const retryM = useMutation({
    mutationFn: retryDocument,
    onSuccess: async () => {
      toast.success("Retrying processing");
      await qc.invalidateQueries({ queryKey: ["documents", selected] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Retry failed"),
  });

  const onFiles = useCallback(
    (list: FileList | File[] | null) => {
      if (!list || !selected) return;
      const files = Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
      if (!files.length) {
        toast.error("Only PDF files are allowed");
        return;
      }
      uploadM.mutate(files);
    },
    [selected, uploadM]
  );

  const items = docsQ.data?.items || [];
  const readyCount = useMemo(() => items.filter((d) => d.status === "ready").length, [items]);

  if (projectsQ.isLoading) return <LoadingState />;
  if (projectsQ.isError) return <ErrorState onRetry={() => void projectsQ.refetch()} />;
  if (!projects.length) {
    return (
      <EmptyState
        title="Create a project first"
        description="Documents belong to a research project."
        action={<a className="rx-btn-primary" href="/projects">Go to Projects</a>}
      />
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">Library</p>
          <h1 className="mt-2 font-display text-4xl text-ink-950 dark:text-white">Documents</h1>
          <p className="mt-2 text-ink-500">
            Upload PDFs for hybrid research. {readyCount} ready of {items.length}.
          </p>
        </div>
        <div>
          <label className="rx-label" htmlFor="doc-project">Project</label>
          <select
            id="doc-project"
            className="rx-input min-w-[220px]"
            value={selected}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        className={`rx-panel border-2 border-dashed p-10 text-center transition ${
          dragging ? "border-accent bg-accent/5" : "border-ink-200 dark:border-ink-700"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          onFiles(e.dataTransfer.files);
        }}
      >
        <p className="font-display text-xl text-ink-900 dark:text-white">Drop PDFs here</p>
        <p className="mt-2 text-sm text-ink-500">or choose files — max 20MB each, PDF only</p>
        <label className="rx-btn-primary mt-5 inline-flex cursor-pointer">
          <input
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="hidden"
            onChange={(e) => {
              onFiles(e.target.files);
              e.target.value = "";
            }}
          />
          {uploadM.isPending ? "Uploading…" : "Select PDFs"}
        </label>
      </div>

      {docsQ.isLoading ? (
        <LoadingState />
      ) : docsQ.isError ? (
        <ErrorState onRetry={() => void docsQ.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title="No documents yet" description="Upload annual reports or research PDFs to ground answers in your files." />
      ) : (
        <ul className="space-y-3">
          {items.map((d) => (
            <li key={d.id} className="rx-panel flex flex-wrap items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink-900 dark:text-white">{d.originalFilename || d.filename}</p>
                <p className="mt-1 text-xs text-ink-500">
                  {formatBytes(d.size)}
                  {d.pageCount != null ? ` · ${d.pageCount} pages` : ""}
                  {d.chunkCount != null ? ` · ${d.chunkCount} chunks` : ""}
                  {d.uploadedAt ? ` · ${formatDate(d.uploadedAt)}` : ""}
                </p>
                <p className="mt-1 text-xs">
                  <span
                    className={
                      d.status === "ready"
                        ? "text-emerald-600"
                        : d.status === "failed"
                          ? "text-red-600"
                          : "text-amber-600"
                    }
                  >
                    {statusLabel(d)}
                  </span>
                  {d.error ? <span className="text-red-500"> — {d.error}</span> : null}
                </p>
              </div>
              <div className="flex gap-2">
                {d.status === "failed" ? (
                  <button
                    type="button"
                    className="rx-btn-secondary"
                    onClick={() => retryM.mutate(d.id)}
                    disabled={retryM.isPending}
                  >
                    Retry
                  </button>
                ) : null}
                <button
                  type="button"
                  className="rx-btn-secondary"
                  onClick={() => {
                    if (confirm(`Remove ${d.originalFilename}?`)) deleteM.mutate(d.id);
                  }}
                  disabled={deleteM.isPending}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
