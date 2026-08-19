import { useParams, Link } from "react-router-dom";
import { useCallback, useState } from "react";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/api/client";
import { PageHeader, LoadingState, ErrorState } from "@/components/Layout/StateViews";
import { AnomalyDetail } from "@/components/AnomalyDetail/AnomalyDetail";
import type { Anomaly } from "@/api/types";

export function AnomalyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const anomalyId = Number(id);

  const fetcher = useCallback(() => api.getAnomaly(anomalyId), [anomalyId]);
  const { data, loading, error, refetch } = useAsync(fetcher, [anomalyId]);
  const [override, setOverride] = useState<Anomaly | null>(null);

  const anomaly = override ?? data;

  return (
    <div>
      <PageHeader
        title="Anomaly Detail"
        subtitle={
          <Link to="/anomalies" className="text-signal hover:underline">
            ← Back to Anomaly Explorer
          </Link>
        }
      />
      <div className="mx-auto max-w-2xl px-8 py-6">
        {loading && <LoadingState label="Loading anomaly" />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && anomaly && (
          <AnomalyDetail anomaly={anomaly} onStatusChange={setOverride} />
        )}
      </div>
    </div>
  );
}
