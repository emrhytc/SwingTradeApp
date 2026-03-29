"use client";

import type { Decision, MarketRegime, RegimeDirection } from "@/lib/types";
import clsx from "clsx";

interface Props {
  symbol: string;
  timeframe: string;
  decision: Decision;
  regime: MarketRegime;
  regimeDirection: RegimeDirection;
  analyzedAt: string;
}

const DECISION_CONFIG = {
  "Suitable": {
    bg: "bg-suitable/10 border-suitable/30",
    text: "text-suitable",
    icon: "✓",
    dot: "bg-suitable",
  },
  "Cautiously Suitable": {
    bg: "bg-cautious/10 border-cautious/30",
    text: "text-cautious",
    icon: "~",
    dot: "bg-cautious",
  },
  "Not Suitable": {
    bg: "bg-danger/10 border-danger/30",
    text: "text-danger",
    icon: "✕",
    dot: "bg-danger",
  },
} as const;

const DIRECTION_COLOR: Record<RegimeDirection, string> = {
  Bullish: "text-suitable",
  Bearish: "text-danger",
  Neutral: "text-muted",
};

export function DecisionBanner({
  symbol,
  timeframe,
  decision,
  regime,
  regimeDirection,
  analyzedAt,
}: Props) {
  const cfg = DECISION_CONFIG[decision];
  const ts = new Date(analyzedAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={clsx("rounded-xl border px-6 py-5", cfg.bg)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* Status dot */}
          <div className={clsx("h-3 w-3 rounded-full", cfg.dot)} />

          {/* Symbol + verdict */}
          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-2xl font-bold text-slate-100">{symbol}</span>
              <span className="text-sm text-muted">{timeframe}</span>
            </div>
            <p className={clsx("mt-0.5 text-lg font-semibold", cfg.text)}>
              {cfg.icon} {decision}
            </p>
          </div>
        </div>

        {/* Regime pill */}
        <div className="flex items-center gap-3">
          <div className="rounded-full border border-surface-border bg-surface px-4 py-1.5 text-sm">
            <span className="text-muted">Regime </span>
            <span className="font-medium text-slate-200">{regime}</span>
            <span className="mx-2 text-muted">·</span>
            <span className={clsx("font-medium", DIRECTION_COLOR[regimeDirection])}>
              {regimeDirection}
            </span>
          </div>
          <span className="text-xs text-muted">Updated {ts}</span>
        </div>
      </div>
    </div>
  );
}
