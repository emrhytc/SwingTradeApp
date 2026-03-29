"use client";

import { useAnalysis } from "@/hooks/useAnalysis";
import { DecisionBanner } from "./DecisionBanner";
import { ScoreGauge } from "./ScoreGauge";
import { ExplanationPanel } from "./ExplanationPanel";
import { TechnicalStatePanel } from "./TechnicalStatePanel";
import { ComponentScoresPanel } from "./ComponentScoresPanel";
import { ChartContainer } from "./ChartContainer";

interface Props {
  symbol: string;
  timeframe: string;
}

export function AnalysisDashboard({ symbol, timeframe }: Props) {
  const { data, isLoading, isError, error, isFetching } = useAnalysis(symbol, timeframe);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm text-muted">Analyzing {symbol} {timeframe}...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/10 p-6 text-center">
        <p className="font-medium text-danger">Analysis failed</p>
        <p className="mt-1 text-sm text-muted">{error?.message}</p>
        <p className="mt-2 text-xs text-muted">
          Check that the backend is running at localhost:8000 and the symbol is valid.
        </p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-4">
      {/* Refresh indicator */}
      {isFetching && (
        <div className="flex items-center gap-2 text-xs text-muted">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
          Refreshing...
        </div>
      )}

      {/* Row 1: Decision banner */}
      <DecisionBanner
        symbol={data.symbol}
        timeframe={data.timeframe}
        decision={data.overall_decision}
        regime={data.regime}
        regimeDirection={data.regime_direction}
        analyzedAt={data.analyzed_at}
      />

      {/* Row 2: Score cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <ScoreGauge label="Overall" score={data.overall_score} size="lg" />
        <ScoreGauge label="Long" score={data.long_score} direction="long" />
        <ScoreGauge label="Short" score={data.short_score} direction="short" />
        <div className="flex flex-col gap-3">
          <StatCard label="Confidence" value={`${data.confidence.toFixed(0)}%`} />
          <StatCard
            label="Risk Level"
            value={data.risk_level}
            colorClass={riskColor(data.risk_level)}
          />
        </div>
      </div>

      {/* Row 3: Chart */}
      {data.chart_data && data.chart_data.length > 0 && (
        <ChartContainer
          bars={data.chart_data}
          indicators={data.indicators}
          symbol={data.symbol}
          timeframe={data.timeframe}
        />
      )}

      {/* Row 4: Component scores */}
      <ComponentScoresPanel components={data.components} />

      {/* Row 5: Explanation + Technical State side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ExplanationPanel
          summary={data.summary}
          positives={data.positive_factors}
          negatives={data.negative_factors}
          conflicts={data.conflicting_factors}
        />
        <TechnicalStatePanel state={data.technical_state} />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  colorClass = "text-slate-100",
}: {
  label: string;
  value: string;
  colorClass?: string;
}) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-lg font-bold ${colorClass}`}>{value}</p>
    </div>
  );
}

function riskColor(risk: string): string {
  return {
    Low: "text-suitable",
    Medium: "text-yellow-400",
    High: "text-cautious",
    Extreme: "text-danger",
  }[risk] ?? "text-slate-100";
}
