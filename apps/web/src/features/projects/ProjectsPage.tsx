import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { createProject, deleteProject, listProjects, updateProject } from "@/features/projects/api";
import { listResearch } from "@/features/research/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDate } from "@/lib/utils";

export function ProjectsPage() {
  const qc = useQueryClient();
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const researchQ = useQuery({ queryKey: ["research", "all"], queryFn: () => listResearch({ limit: 100 }) });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of researchQ.data?.items || []) {
      map.set(r.projectId, (map.get(r.projectId) || 0) + 1);
    }
    return map;
  }, [researchQ.data]);

  const createM = useMutation({
    mutationFn: createProject,
    onSuccess: async () => {
      toast.success("Project created");
      setName("");
      setDescription("");
      await qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Create failed"),
  });

  const updateM = useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; description?: string }) => updateProject(id, body),
    onSuccess: async () => {
      toast.success("Project updated");
      setEditingId(null);
      await qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Update failed"),
  });

  const deleteM = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      toast.success("Project deleted");
      await qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Delete failed"),
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createM.mutate({ name: name.trim(), description: description.trim() });
  }

  if (projectsQ.isLoading) return <LoadingState />;
  if (projectsQ.isError) return <ErrorState onRetry={() => void projectsQ.refetch()} />;

  const items = projectsQ.data?.items || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink-950 dark:text-white">Projects</h1>
        <p className="mt-1 text-sm text-ink-500">Organize research sessions by investigation theme.</p>
      </div>

      <form onSubmit={onCreate} className="rx-panel grid gap-3 p-5 md:grid-cols-[1fr_1.2fr_auto]">
        <div>
          <label className="rx-label" htmlFor="pname">Name</label>
          <input id="pname" className="rx-input" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required placeholder="EV Market Study" />
        </div>
        <div>
          <label className="rx-label" htmlFor="pdesc">Description</label>
          <input id="pdesc" className="rx-input" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} placeholder="Optional notes" />
        </div>
        <div className="flex items-end">
          <button type="submit" className="rx-btn-primary w-full" disabled={createM.isPending}>
            <Plus className="h-4 w-4" /> Create
          </button>
        </div>
      </form>

      {items.length === 0 ? (
        <EmptyState title="No projects yet" description="Create a project before starting research." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => (
            <article key={p.id} className="rx-panel flex flex-col p-5">
              {editingId === p.id ? (
                <EditForm
                  initialName={p.name}
                  initialDescription={p.description}
                  busy={updateM.isPending}
                  onCancel={() => setEditingId(null)}
                  onSave={(n, d) => updateM.mutate({ id: p.id, name: n, description: d })}
                />
              ) : (
                <>
                  <h2 className="font-display text-xl text-ink-950 dark:text-white">{p.name}</h2>
                  <p className="mt-2 flex-1 text-sm text-ink-500">{p.description || "No description"}</p>
                  <div className="mt-4 flex items-center justify-between text-xs text-ink-400">
                    <span>{counts.get(p.id) || 0} sessions</span>
                    <span>{formatDate(p.updatedAt)}</span>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <button type="button" className="rx-btn-secondary" onClick={() => setEditingId(p.id)}>
                      <Pencil className="h-4 w-4" /> Rename
                    </button>
                    <button
                      type="button"
                      className="rx-btn-ghost text-rose-600"
                      onClick={() => {
                        if (confirm("Delete this project?")) deleteM.mutate(p.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function EditForm({
  initialName,
  initialDescription,
  busy,
  onCancel,
  onSave,
}: {
  initialName: string;
  initialDescription: string;
  busy: boolean;
  onCancel: () => void;
  onSave: (name: string, description: string) => void;
}) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(name.trim(), description.trim());
      }}
    >
      <input className="rx-input" value={name} onChange={(e) => setName(e.target.value)} required />
      <textarea className="rx-input min-h-[80px]" value={description} onChange={(e) => setDescription(e.target.value)} />
      <div className="flex gap-2">
        <button type="submit" className="rx-btn-primary" disabled={busy}>Save</button>
        <button type="button" className="rx-btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
