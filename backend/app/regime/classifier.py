"""
Market regime classifier.
Converts indicator data into a discrete regime label and direction.
"""
from app.indicators.trend import TrendResult
from app.indicators.volatility import VolatilityResult
from app.indicators.chop import ChopResult
from app.schemas.analysis import MarketRegime, RegimeDirection


def classify_regime(
    trend: TrendResult,
    vol: VolatilityResult,
    chop: ChopResult,
) -> tuple[MarketRegime, RegimeDirection]:
    """
    Classify market regime into (regime, direction).

    Priority order:
    1. Extreme volatility overrides everything
    2. Strong trend signals → Trending
    3. High chop signals → Choppy
    4. Low ADX, moderate chop → Ranging
    5. Default → Ranging
    """

    # 1. Extreme volatility
    if vol.atr_percentile > 85:
        direction = _classify_direction(trend)
        return MarketRegime.VOLATILE, direction

    # 2. Trending: ADX strong, chop low, ER directional
    if trend.adx >= 25 and chop.chop_index < 50 and chop.efficiency_ratio >= 0.4:
        direction = _classify_direction(trend)
        return MarketRegime.TRENDING, direction

    # 3. Choppy: ADX weak, chop high, ER noisy
    if trend.adx < 20 and chop.chop_index > 61.8 and chop.efficiency_ratio < 0.3:
        direction = _classify_direction(trend)
        return MarketRegime.CHOPPY, direction

    # 4. Moderate trending (ADX borderline)
    if trend.adx >= 20 and chop.chop_index < 55:
        direction = _classify_direction(trend)
        return MarketRegime.TRENDING, direction

    # 5. Default: Ranging
    direction = _classify_direction(trend)
    return MarketRegime.RANGING, direction


def _classify_direction(trend: TrendResult) -> RegimeDirection:
    """Determine directional bias from EMA stack and price position."""
    stack = trend.ema_stack_score

    # Strong bullish: 3 or 4 pairs aligned up, price above 50 EMA
    if stack >= 3 and trend.price_above_ema50:
        return RegimeDirection.BULLISH

    # Strong bearish: 3 or 4 pairs aligned down, price below 50 EMA
    if stack <= -3 and not trend.price_above_ema50:
        return RegimeDirection.BEARISH

    # Moderate bullish
    if stack >= 2 and trend.price_above_ema50 and trend.plus_di > trend.minus_di:
        return RegimeDirection.BULLISH

    # Moderate bearish
    if stack <= -2 and not trend.price_above_ema50 and trend.minus_di > trend.plus_di:
        return RegimeDirection.BEARISH

    return RegimeDirection.NEUTRAL
