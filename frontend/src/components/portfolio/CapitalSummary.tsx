"use client";

import type { AccountResponse, PerformanceResponse } from "@/lib/types";

interface Props {
  account: AccountResponse;
  performance: PerformanceResponse;
  onReset: () => void;
  resetting: boolean;
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function pnlClass(n: number) {
  return n > 0 ? "text-green-400" : n < 0 ? "text-red-400" : "text-muted";
}

export function CapitalSummary({ account, performance, onReset, resetting }: Props) {
  const usedPct = account.allocated_capital / account.total_capital * 100;

  return (
    <div className="space-y-4">
      {/* Top row — main numbers */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card label="Net Portföy Değeri" value={fmt(account.net_equity)}
          sub={<span className={pnlClass(account.unrealized_pnl)}>
            {account.unrealized_pnl >= 0 ? "+" : ""}{fmt(account.unrealized_pnl)} gerçekleşmemiş
          </span>}
          highlight
        />
        <Card label="Müsait Sermaye" value={fmt(account.available_capital)}
          sub={`${account.open_count} / ${account.max_positions} pozisyon açık`}
        />
        <Card label="Gerçekleşen P&L" value={fmt(account.realized_pnl)}
          valueClass={pnlClass(account.realized_pnl)}
          sub={`${performance.total_return_pct >= 0 ? "+" : ""}${performance.total_return_pct.toFixed(2)}% toplam getiri`}
        />
        <Card label="Kullanılan Sermaye" value={fmt(account.allocated_capital)}
          sub={
            <div className="mt-1 w-full rounded-full bg-surface h-1.5">
              <div
                className="h-1.5 rounded-full bg-accent transition-all"
                style={{ width: `${Math.min(usedPct, 100).toFixed(1)}%` }}
              />
            </div>
          }
        />
      </div>

      {/* Performance row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatCell label="Toplam İşlem"  value={String(performance.total_trades)} />
        <StatCell label="Kazanan"       value={String(performance.winning_trades)} valueClass="text-green-400" />
        <StatCell label="Kaybeden"      value={String(performance.losing_trades)}  valueClass="text-red-400" />
        <StatCell label="Kazanma Oranı" value={`${performance.win_rate.toFixed(1)}%`} valueClass={performance.win_rate >= 50 ? "text-green-400" : "text-red-400"} />
        <StatCell label="Ort. P&L"      value={fmt(performance.avg_pnl_usd)} valueClass={pnlClass(performance.avg_pnl_usd)} />
      </div>

      {/* Reset button */}
      <div className="flex justify-end">
        <button
          onClick={onReset}
          disabled={resetting}
          className="rounded-lg border border-red-800 px-4 py-1.5 text-xs text-red-400 hover:bg-red-900/30 disabled:opacity-50 transition-colors"
        >
          {resetting ? "Sıfırlanıyor…" : "Hesabı Sıfırla"}
        </button>
      </div>
    </div>
  );
}

function Card({
  label, value, sub, highlight, valueClass,
}: {
  label: string;
  value: string;
  sub?: React.ReactNode;
  highlight?: boolean;
  valueClass?: string;
}) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-accent/40 bg-accent/5" : "border-surface-border bg-surface-card"}`}>
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className={`text-xl font-semibold font-mono ${valueClass ?? "text-slate-100"}`}>{value}</p>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}

function StatCell({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-card px-3 py-2 text-center">
      <p className="text-[10px] text-muted mb-0.5">{label}</p>
      <p className={`text-sm font-semibold font-mono ${valueClass ?? "text-slate-100"}`}>{value}</p>
    </div>
  );
}
