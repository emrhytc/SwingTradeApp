"use client";

import { useState, useEffect, useCallback } from "react";
import { CapitalSummary } from "./CapitalSummary";
import { OpenPositions } from "./OpenPositions";
import { TradeHistory } from "./TradeHistory";
import { fetchPortfolio, fetchTrades, closeTrade, resetAccount } from "@/lib/api";
import type { PortfolioResponse, TradeResponse } from "@/lib/types";

const REFRESH_INTERVAL_MS = 30_000;

export function PortfolioPage() {
  const [portfolio, setPortfolio]       = useState<PortfolioResponse | null>(null);
  const [closedTrades, setClosedTrades] = useState<TradeResponse[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [closing, setClosing]           = useState<number | null>(null);
  const [resetting, setResetting]       = useState(false);

  const load = useCallback(async () => {
    try {
      const [port, closed] = await Promise.all([
        fetchPortfolio(),
        fetchTrades("closed"),
      ]);
      setPortfolio(port);
      setClosedTrades(closed);
      setError(null);
    } catch (e: any) {
      setError(e.message ?? "Veri yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + periodic refresh
  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  const handleClose = async (id: number) => {
    setClosing(id);
    try {
      await closeTrade(id);
      await load();
    } catch (e: any) {
      alert(`Kapatma hatası: ${e.message}`);
    } finally {
      setClosing(null);
    }
  };

  const handleReset = async () => {
    if (!confirm("Tüm işlemler ve sermaye sıfırlanacak. Emin misiniz?")) return;
    setResetting(true);
    try {
      await resetAccount();
      await load();
    } catch (e: any) {
      alert(`Sıfırlama hatası: ${e.message}`);
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted text-sm">
        Yükleniyor…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/30 p-6 text-center text-sm text-red-400">
        {error}
      </div>
    );
  }

  if (!portfolio) return null;

  return (
    <div className="space-y-6">
      {/* Capital Summary */}
      <section>
        <SectionTitle>Sermaye Özeti</SectionTitle>
        <CapitalSummary
          account={portfolio.account}
          performance={portfolio.performance}
          onReset={handleReset}
          resetting={resetting}
        />
      </section>

      {/* Open Positions */}
      <section>
        <SectionTitle>
          Açık Pozisyonlar
          <span className="ml-2 rounded-full bg-accent/20 px-2 py-0.5 text-[10px] text-accent">
            {portfolio.open_trades.length}
          </span>
          <span className="ml-auto text-[10px] text-muted font-normal">30sn&apos;de bir güncellenir</span>
        </SectionTitle>
        <OpenPositions
          trades={portfolio.open_trades}
          onClose={handleClose}
          closing={closing}
        />
      </section>

      {/* Trade History */}
      <section>
        <SectionTitle>
          İşlem Geçmişi
          <span className="ml-2 rounded-full bg-surface px-2 py-0.5 text-[10px] text-muted">
            {closedTrades.length}
          </span>
        </SectionTitle>
        <TradeHistory trades={closedTrades} />
      </section>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h2 className="text-sm font-semibold text-slate-300">{children}</h2>
    </div>
  );
}
