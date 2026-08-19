import { useState } from "react";
import { useModelStatus } from "@/hooks/useModelStatus";
import { PageHeader, LoadingState, ErrorState } from "@/components/Layout/StateViews";
import { api } from "@/api/client";

export function ModelMonitoringPage() {
  const { data: status, loading, error, refetch } = useModelStatus();
  const [retraining, setRetraining] = useState(false);
  const [retrainMessage, setRetrainMessage] = useState<string | null>(null);

  async function handleRetrain() {
    setRetraining(true);
    setRetrainMessage(null);
    try {
      const result = await api.retrainModel({});
      setRetrainMessage(`Trained model ${result.version} on ${result.rows_used} rows.`);
      refetch();
    } catch (err) {
      setRetrainMessage(err instanceof Error ? err.message : "Retrain failed.");
    } finally {
      setRetraining(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Model Monitoring"
        subtitle="Current model version, training history, and manual retraining"
      />

      <div className="px-8 py-6">
        {loading && <LoadingState label="Loading model status" />}
        {error && <ErrorState message={error} onRetry={refetch} />}

        {!loading && !error && status && (
          <div className="max-w-xl rounded-lg border border-hairline bg-panel px-6 py-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
                  Active model
                </p>
                <p className="mt-1 font-display text-lg font-semibold text-text-primary">
                  {status.model_type} · {status.version}
                </p>
              </div>
              <span
                className={`rounded border px-2 py-0.5 font-mono text-[11px] uppercase ${
                  status.is_active ? "border-signal/40 text-signal" : "border-text-muted/40 text-text-muted"
                }`}
              >
                {status.is_active ? "active" : "inactive"}
              </span>
            </div>

            <dl className="mt-5 grid grid-cols-2 gap-4">
              <Field label="Trained at" value={new Date(status.trained_at).toLocaleString()} />
              <Field label="Contamination" value={status.contamination.toString()} />
              <Field label="Estimators" value={status.n_estimators?.toString() ?? "—"} />
              <Field label="Anomalies detected" value={status.anomalies_detected.toString()} />
            </dl>

            <div className="mt-6 flex items-center gap-3 border-t border-hairline pt-5">
              <button
                onClick={handleRetrain}
                disabled={retraining}
                className="rounded-md bg-signal px-4 py-2 text-sm font-medium text-void transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {retraining ? "Retraining…" : "Retrain model"}
              </button>
              {retrainMessage && <p className="font-mono text-xs text-text-muted">{retrainMessage}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="mt-1 font-mono text-sm text-text-primary">{value}</dd>
    </div>
  );
}
