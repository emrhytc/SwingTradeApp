// Mirrors the Pydantic schemas from backend/app/schemas/analysis.py
// Keep these in sync when the backend schema changes.

export type MarketRegime = "Trending" | "Ranging" | "Choppy" | "Volatile" | "Unknown";
export type RegimeDirection = "Bullish" | "Bearish" | "Neutral";
export type Decision = "Suitable" | "Cautiously Suitable" | "Not Suitable";
export type RiskLevel = "Low" | "Medium" | "High" | "Extreme";
export type StatusLevel = "Strong" | "Moderate" | "Weak" | "Poor" | "Neutral";

export interface ComponentScore {
  score: number;
  raw_score: number;
  label: string;
  status: StatusLevel;
  detail: string;
}

export interface ComponentScores {
  trend: ComponentScore;
  volatility: ComponentScore;
  chop: ComponentScore;
  participation: ComponentScore;
  mtf_alignment: ComponentScore;
  market_context: ComponentScore;
}

export interface TechnicalState {
  ema_alignment: string;
  adx_value: number;
  adx_status: string;
  price_vs_emas: string;
  swing_structure: string;
  trend_direction: RegimeDirection;

  atr_value: number;
  atr_percentile: number;
  bb_width_percentile: number;
  volatility_regime: string;

  efficiency_ratio: number;
  chop_index: number;
  avg_wick_ratio: number;
  chop_status: string;

  relative_volume: number;
  obv_trend: string;
  participation_status: string;

  daily_trend: RegimeDirection;
  h4_trend: RegimeDirection;
  h1_trend: RegimeDirection;
  mtf_conflict: boolean;
  mtf_summary: string;
}

export interface IndicatorSnapshot {
  ema20: number | null;
  ema50: number | null;
  ema100: number | null;
  ema200: number | null;
  adx: number | null;
  plus_di: number | null;
  minus_di: number | null;
  atr: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  obv: number | null;
  relative_volume: number | null;
}

export interface OHLCVBar {
  timestamp: number; // ms
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface AnalysisResponse {
  symbol: string;
  timeframe: string;
  analyzed_at: string;

  overall_decision: Decision;
  overall_score: number;
  long_score: number;
  short_score: number;
  confidence: number;
  risk_level: RiskLevel;

  regime: MarketRegime;
  regime_direction: RegimeDirection;

  components: ComponentScores;

  positive_factors: string[];
  negative_factors: string[];
  conflicting_factors: string[];
  summary: string;

  technical_state: TechnicalState;
  indicators: IndicatorSnapshot;
  chart_data: OHLCVBar[] | null;
}

export const TIMEFRAMES = ["1H", "4H", "1D", "1W"] as const;
export type Timeframe = (typeof TIMEFRAMES)[number];
