"use client";

import type { TradeResponse } from "@/lib/types";

interface Props {
  trades: TradeResponse[];
  onClose: (tradeId: number) => void;
  closing: number | null;
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtDuration(hours: number | null) {
  if (hours === null) return "—";
  if (hours < 24) return `${hours.toFixed(0)}s`;
  const days = Math.floor(hours / 24);
  return `${days}g`;
}

export function OpenPositions({ trades, onClose, closing }: Props) {
  if (trades.length === 0) {
    return (
      <div className="rounded-xl border border-surface-border bg-surface-card p-8 text-center text-sm text-muted">
        Açık pozisyon yok. Analiz sayfasından bir işlem aç.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-surface-border bg-surface-card text-muted">
            <th className="px-3 py-2 text-left">Sembol</th>
            <th className="px-3 py-2 text-left">Zaman D.</th>
            <th className="px-3 py-2 text-left">Yön</th>
            <th className="px-3 py-2 text-right">Giriş</th>
            <th className="px-3 py-2 text-right">Anlık</th>
            <th className="px-3 py-2 text-right">P&L $</th>
            <th className="px-3 py-2 text-right">P&L %</th>
            <th className="px-3 py-2 text-right">Süre</th>
            <th className="px-3 py-2 text-center">İşlem</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const pnl = t.unrealized_pnl_usd ?? 0;
            const pnlPct = t.unrealized_pnl_pct ?? 0;
            const pnlClass = pnl > 0 ? "text-green-400" : pnl < 0 ? "text-red-400" : "text-muted";
            const isClosing = closing === t.id;

            return (
              <tr key={t.id} className="border-b border-surface-border last:border-0 hover:bg-surface-hover transition-colors">
                <td className="px-3 py-2.5 font-mono font-semibold text-slate-100">{t.symbol}</td>
                <td className="px-3 py-2.5 text-muted">{t.timeframe}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                    t.direction === "long"
                      ? "bg-green-900/40 text-green-400"
                      : "bg-red-900/40 text-red-400"
                  }`}>
                    {t.direction === "long" ? "Long" : "Short"}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-right font-mono">{t.entry_price.toFixed(4)}</td>
                <td className="px-3 py-2.5 text-right font-mono">
                  {t.current_price ? t.current_price.toFixed(4) : "—"}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono font-semibold ${pnlClass}`}>
                  {pnl >= 0 ? "+" : ""}{fmt(pnl)}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono ${pnlClass}`}>
                  {pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%
                </td>
                <td className="px-3 py-2.5 text-right text-muted">{fmtDuration(t.duration_hours)}</td>
                <td className="px-3 py-2.5 text-center">
                  <button
                    onClick={() => onClose(t.id)}
                    disabled={isClosing}
                    className="rounded px-2 py-1 text-[10px] font-medium border border-red-800 text-red-400 hover:bg-red-900/30 disabled:opacity-40 transition-colors"
                  >
                    {isClosing ? "…" : "Kapat"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
