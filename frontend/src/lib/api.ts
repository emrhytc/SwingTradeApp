import type { AnalysisResponse } from "./types";

const BASE = "/api/v1";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
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
