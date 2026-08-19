import { useState } from "react";
import { useAnomalies } from "@/hooks/useAnomalies";
import { PageHeader, LoadingState, ErrorState, EmptyState } from "@/components/Layout/StateViews";
import { AnomalyList } from "@/components/AnomalyList/AnomalyList";
import type { AnomalyStatus, Severity } from "@/api/types";

const SEVERITY_OPTIONS: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"];
const STATUS_OPTIONS: (AnomalyStatus | "all")[] = ["all", "new", "acknowledged", "resolved"];

export function AnomalyExplorerPage() {
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [status, setStatus] = useState<AnomalyStatus | "all">("all");

  const { data, loading, error, refetch } = useAnomalies({
    severity: severity === "all" ? undefined : severity,
    status: status === "all" ? undefined : status,
    limit: 100,
  });

  return (
    <div>
      <PageHeader
        title="Anomaly Explorer"
        subtitle="All detected anomalies across services"
        actions={
          <div className="flex gap-2">
            <FilterSelect label="Severity" value={severity} options={SEVERITY_OPTIONS} onChange={setSeverity} />
            <FilterSelect label="Status" value={status} options={STATUS_OPTIONS} onChange={setStatus} />
          </div>
        }
      />

      <div className="px-8 py-6">
        {loading && <LoadingState label="Loading anomalies" />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && data && data.length === 0 && (
          <EmptyState title="No anomalies match these filters" description="Try widening your filters." />
        )}
        {!loading && !error && data && data.length > 0 && <AnomalyList anomalies={data} />}
      </div>
    </div>
  );
}

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-text-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="rounded-md border border-hairline bg-panel-raised px-2 py-1.5 font-mono text-xs text-text-primary focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === "all" ? "All" : opt}
          </option>
        ))}
      </select>
    </label>
  );
}
