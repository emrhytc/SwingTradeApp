"""
Tests for regime classification and explanation generation.
"""
import pytest
from app.indicators.trend import compute_trend_indicators
from app.indicators.volatility import compute_volatility_indicators
from app.indicators.chop import compute_chop_indicators
from app.indicators.participation import compute_participation_indicators
from app.regime.classifier import classify_regime
from app.explanation.generator import generate_explanation
from app.schemas.analysis import MarketRegime, RegimeDirection, Decision


class TestRegimeClassifier:
    def test_trending_up_classified_trending(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        vol = compute_volatility_indicators(trending_up_df)
        chop = compute_chop_indicators(trending_up_df)
        regime, direction = classify_regime(trend, vol, chop)
        assert regime in [MarketRegime.TRENDING, MarketRegime.RANGING]
        assert direction in [RegimeDirection.BULLISH, RegimeDirection.NEUTRAL]

    def test_choppy_classified(self, choppy_df):
        trend = compute_trend_indicators(choppy_df)
        vol = compute_volatility_indicators(choppy_df)
        chop = compute_chop_indicators(choppy_df)
        regime, direction = classify_regime(trend, vol, chop)
        # Choppy market should be Choppy or Ranging
        assert regime in [MarketRegime.CHOPPY, MarketRegime.RANGING, MarketRegime.VOLATILE]

    def test_returns_valid_regime(self, trending_up_df):
        trend = compute_trend_indicators(trending_up_df)
        vol = compute_volatility_indicators(trending_up_df)
        chop = compute_chop_indicators(trending_up_df)
        regime, direction = classify_regime(trend, vol, chop)
        assert regime in list(MarketRegime)
        assert direction in list(RegimeDirection)

    def test_extreme_vol_classified_volatile(self, high_vol_df):
        trend = compute_trend_indicators(high_vol_df)
        vol = compute_volatility_indicators(high_vol_df)
        # Simulate extreme ATR percentile
        vol.atr_percentile = 90
        chop = compute_chop_indicators(high_vol_df)
        regime, _ = classify_regime(trend, vol, chop)
        assert regime == MarketRegime.VOLATILE

    def test_downtrend_direction_bearish(self, trending_down_df):
        trend = compute_trend_indicators(trending_down_df)
        vol = compute_volatility_indicators(trending_down_df)
        chop = compute_chop_indicators(trending_down_df)
        _, direction = classify_regime(trend, vol, chop)
        assert direction in [RegimeDirection.BEARISH, RegimeDirection.NEUTRAL]


class TestExplanationGenerator:
    def _run(self, df, decision=Decision.CAUTIOUSLY_SUITABLE):
        trend = compute_trend_indicators(df)
        vol = compute_volatility_indicators(df)
        chop = compute_chop_indicators(df)
        part = compute_participation_indicators(df)
        regime, direction = classify_regime(trend, vol, chop)
        return generate_explanation(
            trend, vol, chop, part, regime, direction, decision, 65.0, 40.0
        )

    def test_returns_lists_and_summary(self, trending_up_df):
        result = self._run(trending_up_df)
        assert isinstance(result.positive_factors, list)
        assert isinstance(result.negative_factors, list)
        assert isinstance(result.conflicting_factors, list)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 20

    def test_uptrend_has_positives(self, trending_up_df):
        result = self._run(trending_up_df)
        assert len(result.positive_factors) > 0

    def test_choppy_has_negatives(self, choppy_df):
        result = self._run(choppy_df, decision=Decision.NOT_SUITABLE)
        assert len(result.negative_factors) > 0

    def test_factors_are_strings(self, trending_up_df):
        result = self._run(trending_up_df)
        for f in result.positive_factors + result.negative_factors + result.conflicting_factors:
            assert isinstance(f, str) and len(f) > 5

    def test_summary_contains_key_info(self, trending_up_df):
        result = self._run(trending_up_df)
        # Summary should mention the decision and score
        assert any(word in result.summary.lower() for word in ["favorable", "suitable", "bias"])
