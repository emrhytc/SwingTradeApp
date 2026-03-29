"use client";

import clsx from "clsx";

interface Props {
  label: string;
  score: number;
  direction?: "long" | "short";
  size?: "lg" | "sm";
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-suitable";
  if (score >= 60) return "text-cautious";
  return "text-danger";
}

function barColor(score: number): string {
  if (score >= 80) return "bg-suitable";
  if (score >= 60) return "bg-cautious";
  return "bg-danger";
}

function directionLabel(direction?: "long" | "short"): string {
  if (direction === "long") return "↑ Long";
  if (direction === "short") return "↓ Short";
  return "";
}

export function ScoreGauge({ label, score, direction, size = "sm" }: Props) {
  const pct = Math.min(100, Math.max(0, score));

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted">{label}</p>
          {direction && (
            <p className={clsx(
              "text-xs font-medium mt-0.5",
              direction === "long" ? "text-suitable" : "text-danger"
            )}>
              {directionLabel(direction)}
            </p>
          )}
        </div>
        <span className={clsx(
          "font-bold tabular-nums",
          size === "lg" ? "text-4xl" : "text-2xl",
          scoreColor(score)
        )}>
          {score.toFixed(0)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-surface">
        <div
          className={clsx("h-full rounded-full transition-all duration-700", barColor(score))}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Scale ticks */}
      <div className="mt-1 flex justify-between text-[10px] text-muted/50">
        <span>0</span>
        <span className="text-danger/70">60</span>
        <span className="text-cautious/70">80</span>
        <span>100</span>
      </div>
    </div>
  );
}
