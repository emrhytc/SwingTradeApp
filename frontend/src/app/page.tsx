"use client";

import { useState } from "react";
import { AnalysisDashboard } from "@/components/AnalysisDashboard";
import { SymbolSearch } from "@/components/SymbolSearch";
import { TIMEFRAMES, type Timeframe } from "@/lib/types";

export default function Home() {
  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState<Timeframe>("1D");

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="border-b border-surface-border bg-surface-card px-6 py-4">
        <div className="mx-auto max-w-[1600px] flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-7 w-1 rounded-full bg-accent" />
            <h1 className="text-lg font-semibold tracking-tight text-slate-100">
              SwingTradeApp
            </h1>
            <span className="hidden text-xs text-muted sm:block">
              Market Suitability Engine
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Timeframe selector */}
            <div className="flex items-center gap-1 rounded-lg bg-surface p-1">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                    timeframe === tf
                      ? "bg-accent text-white"
                      : "text-muted hover:text-slate-200"
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            {/* Symbol search */}
            <SymbolSearch value={symbol} onSelect={setSymbol} />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6">
        <AnalysisDashboard symbol={symbol} timeframe={timeframe} />
      </main>
    </div>
  );
}
