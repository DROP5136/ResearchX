import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Bookmark, FolderKanban, FlaskConical, Plus } from "lucide-react";
import { listProjects } from "@/features/projects/api";
import { listResearch } from "@/features/research/api";
import { listSavedReports } from "@/features/reports/api";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDate } from "@/lib/utils";

export function DashboardPage() {
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const researchQ = useQuery({ queryKey: ["research", "all"], queryFn: () => listResearch({ limit: 8 }) });
  const savedQ = useQuery({ queryKey: ["saved-reports"], queryFn: listSavedReports });

  if (projectsQ.isLoading || researchQ.isLoading || savedQ.isLoading) {
    return <LoadingState label="Loading dashboard…" />;
  }
  if (projectsQ.isError || researchQ.isError || savedQ.isError) {
    return (
      <ErrorState
        message="Could not load dashboard data."
        onRetry={() => {
          void projectsQ.refetch();
          void researchQ.refetch();
          void savedQ.refetch();
        }}
      />
    );
  }

  const research = researchQ.data?.items || [];
  const active = research.filter((r) => !["completed", "failed"].includes(r.status)).length;
  const projects = projectsQ.data?.items || [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">Workspace</p>
          <h1 className="mt-1 font-display text-3xl text-ink-950 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-ink-500">Live counts from your ResearchX account — no invented metrics.</p>
        </div>
        <Link to="/research/new" className="rx-btn-primary">
          <Plus className="h-4 w-4" />
          Start New Research
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={FlaskConical} label="Research sessions" value={researchQ.data?.total ?? 0} />
        <Stat icon={FlaskConical} label="Active research" value={active} />
        <Stat icon={Bookmark} label="Saved reports" value={savedQ.data?.total ?? 0} />
        <Stat icon={FolderKanban} label="Projects" value={projectsQ.data?.total ?? 0} />
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rx-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-xl">Recent research</h2>
            <Link to="/research/new" className="text-sm font-medium text-accent">New</Link>
          </div>
          {research.length === 0 ? (
            <EmptyState title="No research yet" description="Start your first investigation from a project." />
          ) : (
            <ul className="divide-y divide-ink-100 dark:divide-ink-800">
              {research.map((r) => (
                <li key={r.id} className="flex items-start justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <Link to={r.status === "completed" ? `/research/${r.id}` : `/research/${r.id}/progress`} className="line-clamp-2 font-medium hover:text-accent">
                      {r.query}
                    </Link>
                    <p className="mt-1 text-xs text-ink-500">
                      {r.status} · {formatDate(r.createdAt)}
                    </p>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-ink-400" />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rx-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-xl">Recent projects</h2>
            <Link to="/projects" className="text-sm font-medium text-accent">View all</Link>
          </div>
          {projects.length === 0 ? (
            <EmptyState title="No projects" description="Create a project to organize research sessions." action={<Link className="rx-btn-secondary" to="/projects">Create project</Link>} />
          ) : (
            <ul className="space-y-3">
              {projects.slice(0, 6).map((p) => (
                <li key={p.id} className="rounded-xl border border-ink-100 px-3 py-3 dark:border-ink-800">
                  <Link to={`/projects`} className="font-medium hover:text-accent">{p.name}</Link>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{p.description || "No description"}</p>
                  <p className="mt-2 text-xs text-ink-400">Updated {formatDate(p.updatedAt)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof FlaskConical; label: string; value: number }) {
  return (
    <div className="rx-panel p-4">
      <div className="flex items-center gap-2 text-ink-500">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-[0.08em]">{label}</span>
      </div>
      <p className="mt-3 font-display text-3xl text-ink-950 dark:text-white">{value}</p>
    </div>
  );
}
