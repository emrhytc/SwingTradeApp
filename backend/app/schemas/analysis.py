"""
Core response schemas for the analysis pipeline.
This file defines the contract between backend and frontend.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class MarketRegime(str, Enum):
    TRENDING = "Trending"
    RANGING = "Ranging"
    CHOPPY = "Choppy"
    VOLATILE = "Volatile"
    UNKNOWN = "Unknown"


class RegimeDirection(str, Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class Decision(str, Enum):
    SUITABLE = "Suitable"
    CAUTIOUSLY_SUITABLE = "Cautiously Suitable"
    NOT_SUITABLE = "Not Suitable"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EXTREME = "Extreme"


class StatusLevel(str, Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    POOR = "Poor"
    NEUTRAL = "Neutral"


class ComponentScore(BaseModel):
    score: float = Field(..., ge=0, le=100, description="Normalized 0-100 score")
    raw_score: float = Field(..., description="Pre-normalization weighted contribution")
    label: str
    status: StatusLevel
    detail: str = ""


class ComponentScores(BaseModel):
    trend: ComponentScore
    volatility: ComponentScore
    chop: ComponentScore
    participation: ComponentScore
    mtf_alignment: ComponentScore
    market_context: ComponentScore


class TechnicalState(BaseModel):
    # Trend
    ema_alignment: str  # e.g. "20>50>100>200 (Bullish)"
    adx_value: float
    adx_status: str  # e.g. "Strong Trend (ADX=32)"
    price_vs_emas: str  # e.g. "Price above all EMAs"
    swing_structure: str  # e.g. "Higher Highs / Higher Lows"
    trend_direction: RegimeDirection

    # Volatility
    atr_value: float
    atr_percentile: float
    bb_width_percentile: float
    volatility_regime: str  # e.g. "Expanding from compression"

    # Chop
    efficiency_ratio: float
    chop_index: float
    avg_wick_ratio: float
    chop_status: str

    # Participation
    relative_volume: float
    obv_trend: str  # e.g. "Rising with price (Confirming)"
    participation_status: str

    # MTF
    daily_trend: RegimeDirection
    h4_trend: RegimeDirection
    h1_trend: RegimeDirection
    mtf_conflict: bool
    mtf_summary: str


class IndicatorSnapshot(BaseModel):
    """Raw indicator values for chart overlay use."""
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema100: Optional[float] = None
    ema200: Optional[float] = None
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None
    atr: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    obv: Optional[float] = None
    relative_volume: Optional[float] = None


class OHLCVBar(BaseModel):
    timestamp: int  # Unix timestamp ms (for Lightweight Charts)
    open: float
    high: float
    low: float
    close: float
    volume: float


class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"
    include_chart_data: bool = True


class AnalysisResponse(BaseModel):
    # Identity
    symbol: str
    timeframe: str
    analyzed_at: datetime

    # Top-level verdict
    overall_decision: Decision
    overall_score: float = Field(..., ge=0, le=100)
    long_score: float = Field(..., ge=0, le=100)
    short_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel

    # Regime
    regime: MarketRegime
    regime_direction: RegimeDirection

    # Scored components
    components: ComponentScores

    # Explanation
    positive_factors: List[str]
    negative_factors: List[str]
    conflicting_factors: List[str]
    summary: str

    # Detailed technical state
    technical_state: TechnicalState

    # Raw indicator values (for chart overlays)
    indicators: IndicatorSnapshot

    # Optional OHLCV data for chart rendering
    chart_data: Optional[List[OHLCVBar]] = None


class ScanRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=50)
    timeframe: str = "1D"


class ScanResult(BaseModel):
    symbol: str
    overall_decision: Decision
    overall_score: float
    long_score: float
    short_score: float
    regime: MarketRegime
    regime_direction: RegimeDirection
    summary: str
    error: Optional[str] = None


class ScanResponse(BaseModel):
    results: List[ScanResult]
    scanned_at: datetime
    timeframe: str


class MTFAnalysisResponse(BaseModel):
    symbol: str
    analyzed_at: datetime
    daily: Optional[AnalysisResponse] = None
    h4: Optional[AnalysisResponse] = None
    h1: Optional[AnalysisResponse] = None
    alignment_score: float
    alignment_summary: str
