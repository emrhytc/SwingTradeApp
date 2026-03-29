"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAnalysis } from "@/lib/api";
import type { AnalysisResponse } from "@/lib/types";

export function useAnalysis(symbol: string, timeframe: string) {
  return useQuery<AnalysisResponse, Error>({
    queryKey: ["analysis", symbol, timeframe],
    queryFn: () => fetchAnalysis(symbol, timeframe),
    enabled: symbol.trim().length > 0,
    staleTime: 5 * 60 * 1000, // 5 min — matches backend cache TTL
    retry: 1,
  });
}
