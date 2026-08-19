import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Severity } from "@/api/types";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];
const SEVERITY_COLOR: Record<Severity, string> = {
  low: "#5B7A99",
  medium: "#D9A441",
  high: "#E0813C",
  critical: "#E5484D",
};

export function SeverityBreakdownChart({
  breakdown,
}: {
  breakdown: Partial<Record<Severity, number>>;
}) {
  const data = SEVERITY_ORDER.map((severity) => ({
    severity,
    count: breakdown[severity] ?? 0,
  }));

  return (
    <div className="rounded-lg border border-hairline bg-panel px-5 py-4">
      <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Severity breakdown</p>
      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232935" horizontal={false} />
            <XAxis type="number" tick={{ fill: "#7C8698", fontSize: 11 }} allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="severity"
              tick={{ fill: "#7C8698", fontSize: 11, fontFamily: "JetBrains Mono" }}
              width={64}
            />
            <Tooltip
              contentStyle={{ background: "#1A1F2B", border: "1px solid #232935", borderRadius: 6 }}
              labelStyle={{ color: "#E7E9EE", fontFamily: "JetBrains Mono", fontSize: 12 }}
              itemStyle={{ color: "#E7E9EE", fontSize: 12 }}
              cursor={{ fill: "#232935", opacity: 0.4 }}
            />
            <Bar dataKey="count" radius={[0, 3, 3, 0]}>
              {data.map((entry) => (
                <Cell key={entry.severity} fill={SEVERITY_COLOR[entry.severity]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
