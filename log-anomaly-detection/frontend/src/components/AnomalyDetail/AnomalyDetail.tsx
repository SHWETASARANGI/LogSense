import { useState } from "react";
import type { Anomaly, AnomalyStatus } from "@/api/types";
import { SeverityBadge } from "@/components/AnomalyList/SeverityBadge";
import { SignalMeter } from "@/components/Charts/SignalMeter";
import { api } from "@/api/client";

const STATUS_FLOW: AnomalyStatus[] = ["new", "acknowledged", "resolved"];

export function AnomalyDetail({
  anomaly,
  onStatusChange,
}: {
  anomaly: Anomaly;
  onStatusChange: (updated: Anomaly) => void;
}) {
  const [updating, setUpdating] = useState(false);

  async function handleAdvanceStatus() {
    const currentIndex = STATUS_FLOW.indexOf(anomaly.status);
    const next = STATUS_FLOW[Math.min(currentIndex + 1, STATUS_FLOW.length - 1)];
    if (next === anomaly.status) return;

    setUpdating(true);
    try {
      const updated = await api.updateAnomalyStatus(anomaly.id, next);
      onStatusChange(updated);
    } finally {
      setUpdating(false);
    }
  }

  const featureRows = [
    { label: "Log count", value: anomaly.log_count.toLocaleString() },
    { label: "Error rate", value: `${(anomaly.error_rate * 100).toFixed(2)}%` },
    { label: "Avg latency", value: `${anomaly.avg_latency_ms.toFixed(1)} ms` },
    { label: "P95 latency", value: `${anomaly.p95_latency_ms.toFixed(1)} ms` },
    { label: "Log volume delta", value: `${anomaly.log_volume_delta > 0 ? "+" : ""}${anomaly.log_volume_delta.toFixed(1)}%` },
    { label: "Model version", value: anomaly.model_version },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-hairline bg-panel px-6 py-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Service</p>
            <p className="mt-1 font-display text-xl font-semibold text-text-primary">
              {anomaly.service_name}
            </p>
          </div>
          <SeverityBadge severity={anomaly.severity} />
        </div>

        <div className="mt-5">
          <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Anomaly score</p>
          <div className="mt-2">
            <SignalMeter score={anomaly.anomaly_score} severity={anomaly.severity} />
          </div>
        </div>

        <p className="mt-4 font-mono text-xs text-text-muted">
          {formatWindowRange(anomaly.window_start, anomaly.window_end)}
        </p>
      </div>

      <div className="rounded-lg border border-hairline bg-panel px-6 py-5">
        <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Feature snapshot</p>
        <dl className="mt-3 grid grid-cols-2 gap-4">
          {featureRows.map((row) => (
            <div key={row.label}>
              <dt className="text-xs text-text-muted">{row.label}</dt>
              <dd className="mt-1 font-mono text-sm text-text-primary">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="rounded-lg border border-hairline bg-panel px-6 py-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Triage status</p>
            <p className="mt-1 text-sm text-text-primary">
              Currently <span className="font-medium">{anomaly.status}</span>
            </p>
          </div>
          {anomaly.status !== "resolved" && (
            <button
              onClick={handleAdvanceStatus}
              disabled={updating}
              className="rounded-md bg-signal px-4 py-2 text-sm font-medium text-void transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {updating
                ? "Updating…"
                : anomaly.status === "new"
                ? "Acknowledge"
                : "Mark resolved"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function formatWindowRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  return `${s.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })} → ${e.toLocaleTimeString(
    undefined,
    { timeStyle: "short" }
  )}`;
}
