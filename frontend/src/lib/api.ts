import type { AnalysisResponse, TradeResponse, PortfolioResponse } from "./types";

// Static export: tarayıcı direkt backend'e istek atar (proxy yok)
const BACKEND =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && (window as any).__NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

const BASE = `${BACKEND}/api/v1`;

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, { cache: "no-store", ...options });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchAnalysis(
  symbol: string,
  timeframe: string
): Promise<AnalysisResponse> {
  return apiFetch<AnalysisResponse>(
    `${BASE}/analysis?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&include_chart_data=true`
  );
}

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch(`${BASE}/health`);
}

// ── Paper Trading ─────────────────────────────────────────────────────────────

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  return apiFetch<PortfolioResponse>(`${BASE}/portfolio`);
}

export async function fetchTrades(status?: "open" | "closed"): Promise<TradeResponse[]> {
  const q = status ? `?status=${status}` : "";
  return apiFetch<TradeResponse[]>(`${BASE}/trades${q}`);
}

export async function openTrade(
  symbol: string,
  timeframe: string,
  direction: "long" | "short"
): Promise<TradeResponse> {
  return apiFetch<TradeResponse>(`${BASE}/trades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, timeframe, direction }),
  });
}

export async function closeTrade(tradeId: number): Promise<TradeResponse> {
  return apiFetch<TradeResponse>(`${BASE}/trades/${tradeId}/close`, {
    method: "PUT",
  });
}

export async function resetAccount(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`${BASE}/account/reset`, {
    method: "DELETE",
  });
}
