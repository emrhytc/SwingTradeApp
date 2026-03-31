"use client";

import type { TradeResponse } from "@/lib/types";

interface Props {
  trades: TradeResponse[];
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function TradeHistory({ trades }: Props) {
  if (trades.length === 0) {
    return (
      <div className="rounded-xl border border-surface-border bg-surface-card p-8 text-center text-sm text-muted">
        Henüz kapalı işlem yok.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-surface-border bg-surface-card text-muted">
            <th className="px-3 py-2 text-left">Sembol</th>
            <th className="px-3 py-2 text-left">Yön</th>
            <th className="px-3 py-2 text-right">Giriş</th>
            <th className="px-3 py-2 text-right">Çıkış</th>
            <th className="px-3 py-2 text-right">P&L $</th>
            <th className="px-3 py-2 text-right">P&L %</th>
            <th className="px-3 py-2 text-left">Kapanma</th>
            <th className="px-3 py-2 text-left">Tarih</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const pnl    = t.pnl_usd ?? 0;
            const pnlPct = t.pnl_pct ?? 0;
            const pnlClass = pnl > 0 ? "text-green-400" : pnl < 0 ? "text-red-400" : "text-muted";

            return (
              <tr key={t.id} className="border-b border-surface-border last:border-0 hover:bg-surface-hover transition-colors">
                <td className="px-3 py-2.5 font-mono font-semibold text-slate-100">{t.symbol}</td>
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
                  {t.exit_price ? t.exit_price.toFixed(4) : "—"}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono font-semibold ${pnlClass}`}>
                  {pnl >= 0 ? "+" : ""}{fmt(pnl)}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono ${pnlClass}`}>
                  {pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%
                </td>
                <td className="px-3 py-2.5 text-muted capitalize">
                  {t.close_reason === "manual" ? "Manuel" : t.close_reason === "expired" ? "Süresi Doldu" : "—"}
                </td>
                <td className="px-3 py-2.5 text-muted">{fmtDate(t.exit_time)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
