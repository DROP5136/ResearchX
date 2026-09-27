import { AlertTriangle, FileQuestion, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 text-ink-500">
      <Loader2 className="h-6 w-6 animate-spin text-accent" aria-hidden />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rx-panel flex flex-col items-start gap-3 p-6">
      <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
        <AlertTriangle className="h-5 w-5" />
        <h3 className="font-semibold">{title}</h3>
      </div>
      {message ? <p className="text-sm text-ink-600 dark:text-ink-300">{message}</p> : null}
      {onRetry ? (
        <button type="button" className="rx-btn-secondary" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rx-panel flex flex-col items-center gap-3 px-6 py-12 text-center">
      <FileQuestion className="h-8 w-8 text-ink-400" />
      <h3 className="font-display text-xl text-ink-900 dark:text-ink-50">{title}</h3>
      {description ? <p className="max-w-md text-sm text-ink-500">{description}</p> : null}
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-ink-200/70 dark:bg-ink-800/70", className)} />;
}
