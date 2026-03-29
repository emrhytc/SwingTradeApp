"use client";

import type { TechnicalState } from "@/lib/types";
import clsx from "clsx";

interface Props {
  state: TechnicalState;
}

export function TechnicalStatePanel({ state }: Props) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-5 space-y-4">
      <h2 className="text-sm font-semibold text-slate-200">Technical State</h2>

      <Section title="Trend">
        <Row label="EMA Alignment" value={state.ema_alignment} />
        <Row label="ADX" value={state.adx_status} />
        <Row label="Price vs EMAs" value={state.price_vs_emas} />
        <Row label="Swing Structure" value={state.swing_structure} />
      </Section>

      <Section title="Volatility">
        <Row label="ATR" value={`${state.atr_value.toFixed(4)}`} />
        <Row label="ATR Percentile" value={`${state.atr_percentile.toFixed(0)}th`} />
        <Row label="BB Width Pct" value={`${state.bb_width_percentile.toFixed(0)}th`} />
        <Row label="Regime" value={state.volatility_regime} />
      </Section>

      <Section title="Chop">
        <Row label="Status" value={state.chop_status} />
        <Row label="Efficiency Ratio" value={state.efficiency_ratio.toFixed(3)} />
        <Row label="Chop Index" value={state.chop_index.toFixed(1)} />
        <Row label="Avg Wick Ratio" value={`${(state.avg_wick_ratio * 100).toFixed(0)}%`} />
      </Section>

      <Section title="Participation">
        <Row label="Status" value={state.participation_status} />
        <Row label="Relative Volume" value={`${state.relative_volume.toFixed(2)}x`} />
        <Row label="OBV" value={state.obv_trend} />
      </Section>

      <Section title="Multi-Timeframe">
        <div className="flex gap-2">
          <TFBadge label="1D" direction={state.daily_trend} />
          <TFBadge label="4H" direction={state.h4_trend} />
          <TFBadge label="1H" direction={state.h1_trend} />
        </div>
        <Row
          label="Alignment"
          value={state.mtf_summary}
          forceColor={state.mtf_conflict ? "text-danger" : "text-suitable"}
        />
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted">
        {title}
      </p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  forceColor,
}: {
  label: string;
  value: string;
  forceColor?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-xs text-muted flex-shrink-0">{label}</span>
      <span className={clsx("text-xs text-right text-slate-300 font-medium", forceColor)}>
        {value}
      </span>
    </div>
  );
}

function TFBadge({ label, direction }: { label: string; direction: string }) {
  const colorClass = {
    Bullish: "border-suitable/40 text-suitable bg-suitable/10",
    Bearish: "border-danger/40 text-danger bg-danger/10",
    Neutral: "border-surface-border text-muted bg-surface",
  }[direction] ?? "border-surface-border text-muted";

  const arrow = direction === "Bullish" ? "↑" : direction === "Bearish" ? "↓" : "–";

  return (
    <div className={clsx("flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium", colorClass)}>
      <span>{label}</span>
      <span>{arrow}</span>
    </div>
  );
}
