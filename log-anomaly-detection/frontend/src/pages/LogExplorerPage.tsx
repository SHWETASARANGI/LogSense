import { useState } from "react";
import { useLogs } from "@/hooks/useLogs";
import { PageHeader, LoadingState, ErrorState, EmptyState } from "@/components/Layout/StateViews";

const LEVEL_OPTIONS = ["all", "DEBUG", "INFO", "WARN", "ERROR"] as const;

const LEVEL_COLOR: Record<string, string> = {
  DEBUG: "text-text-muted",
  INFO: "text-signal",
  WARN: "text-severity-medium",
  ERROR: "text-severity-critical",
};

export function LogExplorerPage() {
  const [serviceName, setServiceName] = useState("");
  const [level, setLevel] = useState<(typeof LEVEL_OPTIONS)[number]>("all");

  const { data, loading, error, refetch } = useLogs({
    service_name: serviceName || undefined,
    log_level: level === "all" ? undefined : level,
    limit: 100,
  });

  return (
    <div>
      <PageHeader
        title="Log Explorer"
        subtitle="Browse ingested logs by service, time, and level"
        actions={
          <div className="flex gap-2">
            <input
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              placeholder="Filter by service…"
              className="rounded-md border border-hairline bg-panel-raised px-3 py-1.5 font-mono text-xs text-text-primary placeholder:text-text-muted focus:outline-none"
            />
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value as (typeof LEVEL_OPTIONS)[number])}
              className="rounded-md border border-hairline bg-panel-raised px-2 py-1.5 font-mono text-xs text-text-primary focus:outline-none"
            >
              {LEVEL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt === "all" ? "All levels" : opt}
                </option>
              ))}
            </select>
          </div>
        }
      />

      <div className="px-8 py-6">
        {loading && <LoadingState label="Loading logs" />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && data && data.length === 0 && (
          <EmptyState
            title="No logs found"
            description="Logs appear here once services/ingestion_service.py has loaded data into the logs table."
          />
        )}
        {!loading && !error && data && data.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-hairline">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-hairline bg-panel-raised font-mono text-xs uppercase tracking-wide text-text-muted">
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                  <th className="px-4 py-3 font-medium">Service</th>
                  <th className="px-4 py-3 font-medium">Level</th>
                  <th className="px-4 py-3 font-medium">Message</th>
                </tr>
              </thead>
              <tbody>
                {data.map((log) => (
                  <tr key={log.id} className="border-b border-hairline bg-panel font-mono text-xs last:border-0">
                    <td className="px-4 py-3 text-text-muted">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-text-primary">{log.service_name}</td>
                    <td className={`px-4 py-3 ${LEVEL_COLOR[log.log_level]}`}>{log.log_level}</td>
                    <td className="px-4 py-3 text-text-primary">{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
