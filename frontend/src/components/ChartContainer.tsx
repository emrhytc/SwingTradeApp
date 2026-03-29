"use client";

import { useEffect, useRef } from "react";
import type { OHLCVBar, IndicatorSnapshot } from "@/lib/types";

/**
 * Chart container using TradingView's Lightweight Charts (open-source).
 *
 * ARCHITECTURE NOTE:
 * This component is the designated integration point for TradingView.
 * Two upgrade paths:
 *
 * 1. Full TradingView Charting Library (requires license):
 *    Replace the createChart() call with the TradingView widget initialization.
 *    The `bars` and `indicators` props serve as the data bridge in both cases.
 *
 * 2. Continue with Lightweight Charts (current):
 *    Free, production-quality, no license needed.
 *    Supports candlesticks, volume, line series for EMAs, etc.
 */
interface Props {
  bars: OHLCVBar[];
  indicators: IndicatorSnapshot;
  symbol: string;
  timeframe: string;
}

export function ChartContainer({ bars, indicators, symbol, timeframe }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof import("lightweight-charts")["createChart"]> | null>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    let chart: any;

    const init = async () => {
      const { createChart, CrosshairMode } = await import("lightweight-charts");

      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }

      chart = createChart(containerRef.current!, {
        width: containerRef.current!.clientWidth,
        height: 420,
        layout: {
          background: { color: "#161b27" },
          textColor: "#6b7280",
        },
        grid: {
          vertLines: { color: "#1e2535" },
          horzLines: { color: "#1e2535" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: {
          borderColor: "#1e2535",
        },
        timeScale: {
          borderColor: "#1e2535",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      chartRef.current = chart;

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderDownColor: "#ef4444",
        borderUpColor: "#22c55e",
        wickDownColor: "#ef4444",
        wickUpColor: "#22c55e",
      });

      const ohlcData = bars.map((b) => ({
        time: Math.floor(b.timestamp / 1000) as any,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }));
      candleSeries.setData(ohlcData);

      // Volume histogram
      const volSeries = chart.addHistogramSeries({
        color: "#6366f133",
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });
      volSeries.setData(
        bars.map((b) => ({
          time: Math.floor(b.timestamp / 1000) as any,
          value: b.volume,
          color: b.close >= b.open ? "#22c55e22" : "#ef444422",
        }))
      );

      // EMA lines
      const emaConfigs = [
        { value: indicators.ema20, color: "#f59e0b", label: "EMA20" },
        { value: indicators.ema50, color: "#6366f1", label: "EMA50" },
        { value: indicators.ema100, color: "#ec4899", label: "EMA100" },
        { value: indicators.ema200, color: "#14b8a6", label: "EMA200" },
      ];

      for (const ema of emaConfigs) {
        if (!ema.value) continue;
        const lineSeries = chart.addLineSeries({
          color: ema.color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        // Draw EMA as a single horizontal reference at the latest value
        // (full EMA series would require recomputing from raw bars here)
        lineSeries.setData([
          { time: ohlcData[Math.max(0, ohlcData.length - 100)].time, value: ema.value },
          { time: ohlcData[ohlcData.length - 1].time, value: ema.value },
        ]);
      }

      chart.timeScale().fitContent();

      // Resize observer
      const ro = new ResizeObserver(() => {
        chart.applyOptions({ width: containerRef.current?.clientWidth ?? 800 });
      });
      if (containerRef.current) ro.observe(containerRef.current);

      return () => {
        ro.disconnect();
        chart.remove();
        chartRef.current = null;
      };
    };

    let cleanup: (() => void) | undefined;
    init().then((fn) => { cleanup = fn; });

    return () => {
      cleanup?.();
    };
  }, [bars, indicators]);

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-border">
        <span className="text-xs font-medium text-slate-300">
          {symbol} · {timeframe} · Candlestick
        </span>
        <div className="flex items-center gap-3 text-[10px] text-muted">
          <Dot color="bg-yellow-400" label="EMA20" />
          <Dot color="bg-accent" label="EMA50" />
          <Dot color="bg-pink-500" label="EMA100" />
          <Dot color="bg-teal-400" label="EMA200" />
        </div>
      </div>
      <div ref={containerRef} className="tv-chart-container" />
    </div>
  );
}

function Dot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <div className={`h-1.5 w-3 rounded-full ${color}`} />
      <span>{label}</span>
    </div>
  );
}
