"""
Unit tests for scoring engine and decision logic.
"""
import pytest
from app.indicators.trend import compute_trend_indicators
from app.indicators.volatility import compute_volatility_indicators
from app.indicators.chop import compute_chop_indicators
from app.indicators.participation import compute_participation_indicators
from app.scoring.engine import (
    score_trend, score_volatility, score_chop, score_participation,
    score_mtf, run_scoring_engine, score_to_decision,
    compute_risk_level, compute_confidence,
)
from app.scoring.weights import DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS
from app.schemas.analysis import Decision, RiskLevel


class TestTrendScorer:
    def test_uptrend_scores_higher_long(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        long_score, _ = score_trend(trend, "long")
        short_score, _ = score_trend(trend, "short")
        assert long_score > short_score

    def test_downtrend_scores_higher_short(self, trending_down_df):
        trend = compute_trend_indicators(trending_down_df)
        long_score, _ = score_trend(trend, "long")
        short_score, _ = score_trend(trend, "short")
        assert short_score > long_score

    def test_score_range(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        score, _ = score_trend(trend, "long")
        assert 0 <= score <= 100

    def test_detail_is_string(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        _, detail = score_trend(trend, "long")
        assert isinstance(detail, str) and len(detail) > 0


class TestVolatilityScorer:
    def test_score_range(self, trending_up_df):
        vol = compute_volatility_indicators(trending_up_df)
        score, _ = score_volatility(vol)
        assert 0 <= score <= 100

    def test_extreme_vol_penalized(self, high_vol_df):
        vol = compute_volatility_indicators(high_vol_df)
        # Simulate extreme ATR percentile
        vol.atr_percentile = 92
        vol.volatility_regime = "Extreme"
        score, _ = score_volatility(vol)
        # Score should be low when both ATR and BB are extreme
        assert score < 60

    def test_low_vol_penalized(self, low_vol_df):
        vol = compute_volatility_indicators(low_vol_df)
        vol.atr_percentile = 5  # simulate very low
        score, _ = score_volatility(vol)
        assert score < 50


class TestChopScorer:
    def test_trending_scores_higher(self, trending_up_df, choppy_df):
        chop_trend = compute_chop_indicators(trending_up_df)
        chop_choppy = compute_chop_indicators(choppy_df)
        score_trend, _ = score_chop(chop_trend)
        score_chop, _ = score_chop(chop_choppy)
        assert score_trend > score_chop

    def test_score_range(self, trending_up_df):
        chop = compute_chop_indicators(trending_up_df)
        score, _ = score_chop(chop)
        assert 0 <= score <= 100


class TestParticipationScorer:
    def test_score_range(self, trending_up_df):
        part = compute_participation_indicators(trending_up_df)
        score, _ = score_participation(part, "long")
        assert 0 <= score <= 100


class TestMTFScorer:
    def test_all_aligned_bullish_max_score(self):
        score, detail = score_mtf(4, 4, 4, "long")
        assert score == 100.0

    def test_all_aligned_bearish_max_short(self):
        score, detail = score_mtf(-4, -4, -4, "short")
        assert score == 100.0

    def test_conflict_gives_low_score(self):
        score, detail = score_mtf(4, -4, 4, "long")
        assert score < 50

    def test_partial_alignment(self):
        score_2, _ = score_mtf(4, 4, -4, "long")   # 2 aligned
        score_3, _ = score_mtf(4, 4, 4, "long")    # 3 aligned
        assert score_3 > score_2

    def test_score_range(self):
        score, _ = score_mtf(2, -1, 3, "long")
        assert 0 <= score <= 100


class TestDecisionThresholds:
    def test_high_score_suitable(self):
        assert score_to_decision(85) == Decision.SUITABLE

    def test_mid_score_cautious(self):
        assert score_to_decision(70) == Decision.CAUTIOUSLY_SUITABLE

    def test_low_score_not_suitable(self):
        assert score_to_decision(45) == Decision.NOT_SUITABLE

    def test_exact_threshold_suitable(self):
        assert score_to_decision(80.0) == Decision.SUITABLE

    def test_exact_threshold_cautious(self):
        assert score_to_decision(60.0) == Decision.CAUTIOUSLY_SUITABLE


class TestRiskLevel:
    def test_extreme_risk(self, trending_up_df):
        vol = compute_volatility_indicators(trending_up_df)
        vol.atr_percentile = 90
        assert compute_risk_level(vol) == RiskLevel.EXTREME

    def test_high_risk(self, trending_up_df):
        vol = compute_volatility_indicators(trending_up_df)
        vol.atr_percentile = 75
        assert compute_risk_level(vol) == RiskLevel.HIGH

    def test_low_risk(self, trending_up_df):
        vol = compute_volatility_indicators(trending_up_df)
        vol.atr_percentile = 25
        assert compute_risk_level(vol) == RiskLevel.LOW


class TestFullScoringEngine:
    def test_uptrend_long_score_higher(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        vol = compute_volatility_indicators(trending_up_df)
        chop = compute_chop_indicators(trending_up_df)
        part = compute_participation_indicators(trending_up_df)
        result = run_scoring_engine(trend, vol, chop, part)
        assert result.long_score > result.short_score

    def test_downtrend_short_score_higher(self, trending_down_df):
        trend = compute_trend_indicators(trending_down_df)
        vol = compute_volatility_indicators(trending_down_df)
        chop = compute_chop_indicators(trending_down_df)
        part = compute_participation_indicators(trending_down_df)
        result = run_scoring_engine(trend, vol, chop, part)
        assert result.short_score > result.long_score

    def test_score_bounds(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        vol = compute_volatility_indicators(trending_up_df)
        chop = compute_chop_indicators(trending_up_df)
        part = compute_participation_indicators(trending_up_df)
        result = run_scoring_engine(trend, vol, chop, part)
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.long_score <= 100
        assert 0 <= result.short_score <= 100
        assert 0 <= result.confidence <= 100

    def test_choppy_market_low_score(self, choppy_df):
        trend = compute_trend_indicators(choppy_df)
        vol = compute_volatility_indicators(choppy_df)
        chop = compute_chop_indicators(choppy_df)
        part = compute_participation_indicators(choppy_df)
        result = run_scoring_engine(trend, vol, chop, part)
        # A choppy market should have a lower overall score
        assert result.overall_score < 75

    def test_weights_validated(self):
        from app.scoring.weights import ScoringWeights
        with pytest.raises(ValueError, match="sum to 1.0"):
            bad_weights = ScoringWeights.__new__(ScoringWeights)
            object.__setattr__(bad_weights, "trend", 0.5)
            object.__setattr__(bad_weights, "volatility", 0.5)
            object.__setattr__(bad_weights, "chop", 0.5)
            object.__setattr__(bad_weights, "participation", 0.5)
            object.__setattr__(bad_weights, "mtf", 0.5)
            object.__setattr__(bad_weights, "context", 0.5)
            bad_weights.validate()
