// SignalMeter.tsx
// The visual signature of LogSense: every anomaly_score renders as a
// tick-marked amplitude meter rather than a plain number or generic progress
// bar. It's meant to evoke an oscilloscope / signal-monitoring instrument -
// reinforcing that the whole product is about reading deviation in a signal.
// Purely derived from the real anomaly_score (no fabricated data).

import type { Severity } from "@/api/types";

const SEVERITY_COLOR: Record<Severity, string> = {
  low: "#5B7A99",
  medium: "#D9A441",
  high: "#E0813C",
  critical: "#E5484D",
};

const TICKS = 20;

export function SignalMeter({
  score,
  severity,
  size = "md",
}: {
  score: number;
  severity: Severity;
  size?: "sm" | "md";
}) {
  const filledTicks = Math.round(score * TICKS);
  const color = SEVERITY_COLOR[severity];
  const height = size === "sm" ? "h-3" : "h-4";
  const barGap = size === "sm" ? "gap-[2px]" : "gap-[3px]";

  return (
    <div className="flex items-center gap-3">
      <div className={`flex ${barGap} ${height}`} role="img" aria-label={`Anomaly score ${score.toFixed(2)}`}>
        {Array.from({ length: TICKS }).map((_, i) => {
          const isFilled = i < filledTicks;
          const isPeak = i === filledTicks - 1 && isFilled;
          return (
            <span
              key={i}
              className="w-[3px] rounded-[1px] transition-colors"
              style={{
                backgroundColor: isFilled ? color : "#232935",
                height: "100%",
                boxShadow: isPeak ? `0 0 6px 0 ${color}` : undefined,
              }}
            />
          );
        })}
      </div>
      <span className="font-mono text-sm tabular-nums" style={{ color }}>
        {score.toFixed(2)}
      </span>
    </div>
  );
}
