import { useDashboard } from "@/hooks/useDashboard";
import { useAnomalies } from "@/hooks/useAnomalies";
import { PageHeader, LoadingState, ErrorState } from "@/components/Layout/StateViews";
import { SummaryCards } from "@/components/Dashboard/SummaryCards";
import { SeverityBreakdownChart } from "@/components/Dashboard/SeverityBreakdownChart";
import { AnomalyList } from "@/components/AnomalyList/AnomalyList";

export function DashboardPage() {
  const { data: summary, loading, error, refetch } = useDashboard(24 * 30);
  const { data: recentAnomalies } = useAnomalies({ limit: 6 });

  if (loading) return <LoadingState label="Loading dashboard" />;
  if (error || !summary) return <ErrorState message={error ?? "Could not load dashboard."} onRetry={refetch} />;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={
          summary.model_version
            ? `Active model ${summary.model_version} · trained ${new Date(
                summary.model_trained_at ?? ""
              ).toLocaleDateString()}`
            : "No model trained yet"
        }
      />

      <div className="flex flex-col gap-6 px-8 py-6">
        <SummaryCards summary={summary} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SeverityBreakdownChart breakdown={summary.severity_breakdown} />
          </div>
          <div className="lg:col-span-2">
            <p className="mb-3 font-mono text-xs uppercase tracking-wide text-text-muted">
              Recent anomalies
            </p>
            {recentAnomalies && recentAnomalies.length > 0 ? (
              <AnomalyList anomalies={recentAnomalies} />
            ) : (
              <div className="rounded-lg border border-hairline bg-panel px-5 py-8 text-center text-sm text-text-muted">
                No anomalies detected yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
