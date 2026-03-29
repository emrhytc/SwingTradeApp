"use client";

import type { ComponentScores } from "@/lib/types";
import clsx from "clsx";

interface Props {
  components: ComponentScores;
}

const COMPONENT_ORDER = [
  { key: "trend", label: "Trend Quality", weight: "25%" },
  { key: "volatility", label: "Volatility", weight: "20%" },
  { key: "chop", label: "Chop / Cleanliness", weight: "20%" },
  { key: "participation", label: "Participation", weight: "15%" },
  { key: "mtf_alignment", label: "MTF Alignment", weight: "15%" },
  { key: "market_context", label: "Market Context", weight: "5%" },
] as const;

function barColor(score: number): string {
  if (score >= 75) return "bg-suitable";
  if (score >= 50) return "bg-yellow-400";
  if (score >= 30) return "bg-cautious";
  return "bg-danger";
}

function statusDot(status: string): string {
  return {
    Strong: "bg-suitable",
    Moderate: "bg-yellow-400",
    Weak: "bg-cautious",
    Poor: "bg-danger",
    Neutral: "bg-muted",
  }[status] ?? "bg-muted";
}

export function ComponentScoresPanel({ components }: Props) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-5">
      <h2 className="mb-4 text-sm font-semibold text-slate-200">Component Scores</h2>
      <div className="space-y-3">
        {COMPONENT_ORDER.map(({ key, label, weight }) => {
          const comp = components[key];
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className={clsx("h-2 w-2 rounded-full", statusDot(comp.status))} />
                  <span className="text-xs text-slate-300">{label}</span>
                  <span className="text-[10px] text-muted">({weight})</span>
                </div>
                <span className={clsx(
                  "text-xs font-mono font-bold tabular-nums",
                  comp.score >= 75 ? "text-suitable"
                  : comp.score >= 50 ? "text-yellow-400"
                  : comp.score >= 30 ? "text-cautious"
                  : "text-danger"
                )}>
                  {comp.score.toFixed(0)}
                </span>
              </div>
              {/* Bar */}
              <div className="h-1 w-full overflow-hidden rounded-full bg-surface">
                <div
                  className={clsx("h-full rounded-full transition-all duration-500", barColor(comp.score))}
                  style={{ width: `${comp.score}%` }}
                />
              </div>
              {/* Detail tooltip */}
              {comp.detail && (
                <p className="mt-0.5 truncate text-[10px] text-muted" title={comp.detail}>
                  {comp.detail}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
