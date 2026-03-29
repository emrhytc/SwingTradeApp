"""
Unit tests for indicator computation functions.
All tests use synthetic data — no network calls.
"""
import pytest
import numpy as np
from app.indicators.trend import compute_emas, compute_adx, detect_swing_structure, compute_trend_indicators
from app.indicators.volatility import compute_atr, compute_bollinger_bands, compute_volatility_indicators
from app.indicators.chop import compute_efficiency_ratio, compute_chop_index, compute_chop_indicators
from app.indicators.participation import compute_obv, compute_relative_volume, compute_participation_indicators


# ── Trend ──────────────────────────────────────────────────────────────

class TestEMAs:
    def test_ema_columns_created(self, trending_up_df):
        df = compute_emas(trending_up_df)
        for p in [20, 50, 100, 200]:
            assert f"ema{p}" in df.columns

    def test_ema_uptrend_stack(self, trending_up_df):
        """In a strong uptrend, EMA20 > EMA50 > EMA100 > EMA200 at the end."""
        df = compute_emas(trending_up_df)
        last = df.iloc[-1]
        assert last["ema20"] > last["ema50"]
        assert last["ema50"] > last["ema100"]

    def test_ema_downtrend_stack(self, trending_down_df):
        """In a strong downtrend, EMA20 < EMA50 at the end."""
        df = compute_emas(trending_down_df)
        last = df.iloc[-1]
        assert last["ema20"] < last["ema50"]

    def test_ema_no_nan_after_warmup(self, trending_up_df):
        df = compute_emas(trending_up_df)
        # After 200 bars, no NaN should remain
        assert df["ema200"].iloc[200:].isna().sum() == 0


class TestADX:
    def test_adx_columns_created(self, trending_up_df):
        df = compute_adx(trending_up_df)
        assert "adx" in df.columns
        assert "plus_di" in df.columns
        assert "minus_di" in df.columns

    def test_adx_range(self, trending_up_df):
        df = compute_adx(trending_up_df)
        valid = df["adx"].dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_adx_uptrend_plus_di_dominant(self, trending_up_df):
        """In an uptrend, +DI should generally exceed -DI."""
        df = compute_adx(trending_up_df)
        last = df.dropna().iloc[-1]
        assert last["plus_di"] > last["minus_di"]

    def test_adx_downtrend_minus_di_dominant(self, trending_down_df):
        df = compute_adx(trending_down_df)
        last = df.dropna().iloc[-1]
        assert last["minus_di"] > last["plus_di"]

    def test_adx_trending_higher_than_choppy(self, trending_up_df, choppy_df):
        """ADX should be higher for a trending market than a choppy one."""
        df_t = compute_adx(trending_up_df)
        df_c = compute_adx(choppy_df)
        adx_trend = df_t["adx"].dropna().iloc[-1]
        adx_chop = df_c["adx"].dropna().iloc[-1]
        assert adx_trend > adx_chop


class TestSwingStructure:
    def test_uptrend_returns_bullish_structure(self, trending_up_df):
        score, desc = detect_swing_structure(trending_up_df)
        assert score == 1

    def test_downtrend_returns_bearish_structure(self, trending_down_df):
        score, desc = detect_swing_structure(trending_down_df)
        assert score == -1


class TestTrendResult:
    def test_result_fields_populated(self, trending_up_df):
        result = compute_trend_indicators(trending_up_df)
        assert result.adx >= 0
        assert 0 <= result.price_above_count <= 4
        assert -4 <= result.ema_stack_score <= 4
        assert result.swing_structure in [-1, 0, 1]

    def test_uptrend_positive_stack(self, trending_up_df):
        result = compute_trend_indicators(trending_up_df)
        assert result.ema_stack_score > 0

    def test_downtrend_negative_stack(self, trending_down_df):
        result = compute_trend_indicators(trending_down_df)
        assert result.ema_stack_score < 0


# ── Volatility ─────────────────────────────────────────────────────────

class TestATR:
    def test_atr_positive(self, trending_up_df):
        atr = compute_atr(trending_up_df)
        assert (atr.dropna() > 0).all()

    def test_high_vol_has_higher_atr(self, trending_up_df, high_vol_df):
        atr_normal = compute_atr(trending_up_df).dropna().mean()
        atr_high = compute_atr(high_vol_df).dropna().mean()
        assert atr_high > atr_normal


class TestBollingerBands:
    def test_bb_columns_present(self, trending_up_df):
        df = compute_bollinger_bands(trending_up_df)
        for col in ["bb_upper", "bb_middle", "bb_lower", "bb_width"]:
            assert col in df.columns

    def test_bb_order(self, trending_up_df):
        df = compute_bollinger_bands(trending_up_df).dropna()
        assert (df["bb_upper"] >= df["bb_middle"]).all()
        assert (df["bb_middle"] >= df["bb_lower"]).all()

    def test_bb_width_positive(self, trending_up_df):
        df = compute_bollinger_bands(trending_up_df).dropna()
        assert (df["bb_width"] > 0).all()


class TestVolatilityResult:
    def test_percentile_range(self, trending_up_df):
        result = compute_volatility_indicators(trending_up_df)
        assert 0 <= result.atr_percentile <= 100
        assert 0 <= result.bb_width_percentile <= 100

    def test_extreme_vol_detected(self, high_vol_df):
        result = compute_volatility_indicators(high_vol_df)
        # High vol data should have higher ATR percentile
        assert result.atr_percentile > 50

    def test_low_vol_has_low_percentile(self, low_vol_df):
        result = compute_volatility_indicators(low_vol_df)
        assert result.atr_percentile < 50


# ── Chop ───────────────────────────────────────────────────────────────

class TestEfficiencyRatio:
    def test_range_0_to_1(self, trending_up_df):
        er = compute_efficiency_ratio(trending_up_df["close"])
        valid = er.dropna()
        assert (valid >= 0).all()
        assert (valid <= 1).all()

    def test_trending_er_higher(self, trending_up_df, choppy_df):
        er_trend = compute_efficiency_ratio(trending_up_df["close"]).dropna().mean()
        er_chop = compute_efficiency_ratio(choppy_df["close"]).dropna().mean()
        assert er_trend > er_chop


class TestChopIndex:
    def test_range(self, trending_up_df):
        ci = compute_chop_index(trending_up_df)
        valid = ci.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_choppy_market_high_ci(self, choppy_df):
        ci = compute_chop_index(choppy_df).dropna()
        # Choppy market should have CI above midline
        assert ci.mean() > 50

    def test_trending_market_low_ci(self, trending_up_df):
        ci = compute_chop_index(trending_up_df).dropna()
        assert ci.mean() < 65  # not perfectly strict but should be lower


class TestChopResult:
    def test_clean_fields(self, trending_up_df):
        result = compute_chop_indicators(trending_up_df)
        assert 0 <= result.efficiency_ratio <= 1
        assert 0 <= result.chop_index <= 100
        assert 0 <= result.avg_wick_ratio <= 1
        assert result.chop_label in ["Clean Trend", "Moderate", "Choppy", "Very Choppy"]


# ── Participation ──────────────────────────────────────────────────────

class TestOBV:
    def test_obv_length(self, trending_up_df):
        obv = compute_obv(trending_up_df)
        assert len(obv) == len(trending_up_df)

    def test_obv_rises_in_uptrend(self, trending_up_df):
        obv = compute_obv(trending_up_df)
        # OBV at end should be higher than at start for uptrend
        assert obv.iloc[-1] > obv.iloc[0]

    def test_obv_falls_in_downtrend(self, trending_down_df):
        obv = compute_obv(trending_down_df)
        assert obv.iloc[-1] < obv.iloc[0]


class TestRelativeVolume:
    def test_relative_volume_positive(self, trending_up_df):
        rv = compute_relative_volume(trending_up_df)
        assert rv > 0

    def test_relative_volume_near_one_average(self, trending_up_df):
        # With random volume from uniform distribution, rel vol should be near 1
        rv = compute_relative_volume(trending_up_df)
        assert 0.3 < rv < 3.0


class TestParticipationResult:
    def test_fields_populated(self, trending_up_df):
        result = compute_participation_indicators(trending_up_df)
        assert result.relative_volume > 0
        assert isinstance(result.obv_aligned, bool)
        assert 0 <= result.breakout_volume_quality <= 1
        assert result.participation_label in [
            "Strong", "Moderate", "Weak", "Absent", "Diverging (OBV conflict)"
        ]
