import { Link } from "react-router-dom";
import type { Anomaly } from "@/api/types";
import { SeverityBadge } from "./SeverityBadge";
import { SignalMeter } from "@/components/Charts/SignalMeter";

export function AnomalyList({ anomalies }: { anomalies: Anomaly[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-hairline">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-hairline bg-panel-raised font-mono text-xs uppercase tracking-wide text-text-muted">
            <th className="px-4 py-3 font-medium">Service</th>
            <th className="px-4 py-3 font-medium">Window</th>
            <th className="px-4 py-3 font-medium">Score</th>
            <th className="px-4 py-3 font-medium">Severity</th>
            <th className="px-4 py-3 font-medium">Error rate</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((anomaly) => (
            <tr
              key={anomaly.id}
              className="border-b border-hairline bg-panel last:border-0 hover:bg-panel-raised"
            >
              <td className="px-4 py-3">
                <Link
                  to={`/anomalies/${anomaly.id}`}
                  className="font-medium text-text-primary hover:text-signal"
                >
                  {anomaly.service_name}
                </Link>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-text-muted">
                {formatWindow(anomaly.window_start)}
              </td>
              <td className="px-4 py-3">
                <SignalMeter score={anomaly.anomaly_score} severity={anomaly.severity} size="sm" />
              </td>
              <td className="px-4 py-3">
                <SeverityBadge severity={anomaly.severity} />
              </td>
              <td className="px-4 py-3 font-mono text-xs text-text-primary">
                {(anomaly.error_rate * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-3">
                <StatusPill status={anomaly.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatWindow(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusPill({ status }: { status: Anomaly["status"] }) {
  const styles: Record<Anomaly["status"], string> = {
    new: "border-signal/40 text-signal",
    acknowledged: "border-severity-medium/40 text-severity-medium",
    resolved: "border-text-muted/40 text-text-muted",
  };
  return (
    <span className={`rounded border px-2 py-0.5 font-mono text-[11px] uppercase ${styles[status]}`}>
      {status}
    </span>
  );
}
