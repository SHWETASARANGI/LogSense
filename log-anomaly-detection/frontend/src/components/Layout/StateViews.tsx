import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between border-b border-hairline px-8 py-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-text-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-16 text-center font-mono text-sm text-text-muted">
      <span className="h-2 w-2 animate-pulse rounded-full bg-signal" />
      {label}…
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-severity-critical/30 bg-severity-critical/5 px-5 py-4">
      <p className="text-sm text-severity-critical">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md border border-severity-critical/40 px-3 py-1.5 text-xs font-medium text-severity-critical transition-colors hover:bg-severity-critical/10"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-16 text-center">
      <p className="font-display text-sm font-medium text-text-primary">{title}</p>
      {description && <p className="text-sm text-text-muted">{description}</p>}
    </div>
  );
}
