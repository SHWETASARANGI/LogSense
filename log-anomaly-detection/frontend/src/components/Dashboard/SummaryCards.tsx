import type { DashboardSummary } from "@/api/types";

export function SummaryCards({ summary }: { summary: DashboardSummary }) {
  const cards = [
    {
      label: "Active anomalies",
      value: summary.active_anomalies,
      accent: summary.active_anomalies > 0 ? "text-severity-high" : "text-text-primary",
    },
    {
      label: "Total anomalies",
      value: summary.total_anomalies,
      accent: "text-text-primary",
    },
    {
      label: "Avg. error rate",
      value: `${(summary.avg_error_rate * 100).toFixed(1)}%`,
      accent: "text-text-primary",
    },
    {
      label: "Avg. anomaly score",
      value: summary.avg_anomaly_score.toFixed(2),
      accent: "text-signal",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-hairline bg-panel px-5 py-4">
          <p className="font-mono text-xs uppercase tracking-wide text-text-muted">{card.label}</p>
          <p className={`mt-2 font-display text-2xl font-semibold ${card.accent}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
