"""
Explanation generator.
Converts scored components and indicator data into human-readable
positive, negative, and conflicting factor lists plus a summary sentence.
This is a rule-based NLG layer — each rule fires independently and
contributes to one of the three lists.
"""
from typing import List, Tuple
from dataclasses import dataclass

from app.indicators.trend import TrendResult
from app.indicators.volatility import VolatilityResult
from app.indicators.chop import ChopResult
from app.indicators.participation import ParticipationResult
from app.schemas.analysis import MarketRegime, RegimeDirection, Decision


@dataclass
class ExplanationResult:
    positive_factors: List[str]
    negative_factors: List[str]
    conflicting_factors: List[str]
    summary: str


def generate_explanation(
    trend: TrendResult,
    vol: VolatilityResult,
    chop: ChopResult,
    part: ParticipationResult,
    regime: MarketRegime,
    regime_direction: RegimeDirection,
    decision: Decision,
    long_score: float,
    short_score: float,
) -> ExplanationResult:

    positives: List[str] = []
    negatives: List[str] = []
    conflicts: List[str] = []

    # ── Trend factors ──────────────────────────────────────

    if trend.ema_stack_score >= 3:
        positives.append(
            f"EMAs are in full bullish alignment (20>50>100>200), indicating a clean uptrend."
        )
    elif trend.ema_stack_score <= -3:
        positives.append(
            f"EMAs are in full bearish alignment (20<50<100<200), indicating a clean downtrend."
        )
    elif abs(trend.ema_stack_score) >= 2:
        conflicts.append(
            f"EMA alignment is partial (score {trend.ema_stack_score:+d}/4) — trend is developing but not confirmed."
        )
    else:
        negatives.append(
            f"EMAs are mixed or crossed (score {trend.ema_stack_score:+d}/4) — no clear trend structure."
        )

    if trend.adx >= 30:
        positives.append(f"ADX = {trend.adx:.1f}, indicating a strong trend with directional conviction.")
    elif trend.adx >= 25:
        positives.append(f"ADX = {trend.adx:.1f}, indicating a moderate trend — suitable for swing setups.")
    elif trend.adx >= 20:
        conflicts.append(f"ADX = {trend.adx:.1f} is borderline — trend is weak and may not support follow-through.")
    else:
        negatives.append(f"ADX = {trend.adx:.1f} is below 20, indicating no meaningful trend direction.")

    if trend.price_above_count == 4:
        positives.append("Price is trading above all four EMAs (20/50/100/200) — bullish positioning.")
    elif trend.price_above_count == 0:
        positives.append("Price is trading below all four EMAs — bearish positioning for short setups.")
    elif trend.price_above_count == 2:
        conflicts.append(
            f"Price is above {trend.price_above_count}/4 EMAs — mixed positioning with no clear bias."
        )

    if trend.swing_structure == 1:
        positives.append(f"Swing structure shows {trend.swing_detail}, confirming bullish momentum.")
    elif trend.swing_structure == -1:
        positives.append(f"Swing structure shows {trend.swing_detail}, confirming bearish momentum.")
    else:
        conflicts.append(f"Swing structure is mixed: {trend.swing_detail}.")

    # ── Volatility factors ─────────────────────────────────

    if 30 <= vol.atr_percentile <= 70:
        positives.append(
            f"ATR is at the {vol.atr_percentile:.0f}th percentile — in the goldilocks zone for swing trading."
        )
    elif vol.atr_percentile > 85:
        negatives.append(
            f"ATR is at the {vol.atr_percentile:.0f}th percentile — extremely high volatility increases stop-out risk."
        )
    elif vol.atr_percentile < 15:
        negatives.append(
            f"ATR is at the {vol.atr_percentile:.0f}th percentile — very low volatility suggests weak follow-through."
        )
    else:
        conflicts.append(f"ATR is at the {vol.atr_percentile:.0f}th percentile — borderline volatility environment.")

    if vol.is_expanding:
        positives.append("Volatility is expanding from a recent low — a favorable setup for trend continuation entries.")
    elif vol.is_compressing:
        conflicts.append("Volatility is compressing — wait for breakout confirmation before entering.")
    elif vol.volatility_regime == "Extreme":
        negatives.append("Volatility regime is extreme — risk of erratic moves and wide intraday swings.")

    # ── Chop factors ───────────────────────────────────────

    if chop.efficiency_ratio >= 0.5:
        positives.append(
            f"Efficiency Ratio = {chop.efficiency_ratio:.2f} — price is moving directionally with minimal noise."
        )
    elif chop.efficiency_ratio < 0.25:
        negatives.append(
            f"Efficiency Ratio = {chop.efficiency_ratio:.2f} — price is moving randomly. Swing entries will be punished."
        )
    else:
        conflicts.append(f"Efficiency Ratio = {chop.efficiency_ratio:.2f} — moderate noise in price action.")

    if chop.chop_index < 38.2:
        positives.append(f"Chop Index = {chop.chop_index:.1f} — market is in a trending state.")
    elif chop.chop_index > 61.8:
        negatives.append(f"Chop Index = {chop.chop_index:.1f} — market is highly choppy. Risk of false breakouts is elevated.")
    else:
        conflicts.append(f"Chop Index = {chop.chop_index:.1f} — transitional state, neither strongly trending nor choppy.")

    if chop.avg_wick_ratio > 0.6:
        negatives.append(
            f"Average wick ratio is {chop.avg_wick_ratio:.0%} — bars have dominant wicks indicating rejection and indecision."
        )
    elif chop.avg_wick_ratio < 0.3:
        positives.append(f"Bar bodies are clean with low wick ratio ({chop.avg_wick_ratio:.0%}), indicating decisive price movement.")

    # ── Participation factors ──────────────────────────────

    if part.relative_volume >= 1.5:
        positives.append(f"Relative volume = {part.relative_volume:.1f}x average — strong participation backing the move.")
    elif part.relative_volume < 0.7:
        negatives.append(f"Relative volume = {part.relative_volume:.1f}x average — low participation reduces breakout reliability.")
    else:
        conflicts.append(f"Relative volume = {part.relative_volume:.1f}x average — participation is average, not confirming.")

    if part.obv_aligned:
        positives.append("OBV is trending in alignment with price — institutional accumulation/distribution is confirming direction.")
    else:
        negatives.append("OBV is diverging from price — potential distribution or lack of real conviction behind the move.")

    # ── Build summary ──────────────────────────────────────

    summary = _build_summary(
        decision, long_score, short_score, regime, regime_direction,
        trend, vol, chop, part
    )

    return ExplanationResult(
        positive_factors=positives,
        negative_factors=negatives,
        conflicting_factors=conflicts,
        summary=summary,
    )


def _build_summary(
    decision: Decision,
    long_score: float,
    short_score: float,
    regime: MarketRegime,
    direction: RegimeDirection,
    trend: TrendResult,
    vol: VolatilityResult,
    chop: ChopResult,
    part: ParticipationResult,
) -> str:
    """Generate a single-paragraph plain English summary."""

    verdict_map = {
        Decision.SUITABLE: "conditions are favorable",
        Decision.CAUTIOUSLY_SUITABLE: "conditions are cautiously favorable",
        Decision.NOT_SUITABLE: "conditions are not favorable",
    }
    verdict = verdict_map[decision]

    dominant = "long" if long_score >= short_score else "short"
    dom_score = max(long_score, short_score)

    regime_desc = {
        MarketRegime.TRENDING: "trending",
        MarketRegime.RANGING: "ranging",
        MarketRegime.CHOPPY: "choppy",
        MarketRegime.VOLATILE: "highly volatile",
        MarketRegime.UNKNOWN: "undefined",
    }[regime]

    key_positives = []
    key_negatives = []

    if trend.adx >= 25:
        key_positives.append(f"ADX={trend.adx:.0f}")
    else:
        key_negatives.append(f"weak ADX={trend.adx:.0f}")

    if abs(trend.ema_stack_score) >= 3:
        align = "bullish" if trend.ema_stack_score > 0 else "bearish"
        key_positives.append(f"full EMA {align} alignment")
    else:
        key_negatives.append("mixed EMA alignment")

    if chop.chop_index > 61.8:
        key_negatives.append(f"high chop ({chop.chop_index:.0f})")
    elif chop.chop_index < 45:
        key_positives.append(f"clean structure (CI={chop.chop_index:.0f})")

    if not part.obv_aligned:
        key_negatives.append("OBV divergence")
    elif part.relative_volume >= 1.3:
        key_positives.append(f"strong volume ({part.relative_volume:.1f}x)")

    if vol.atr_percentile > 80:
        key_negatives.append("extreme volatility")
    elif vol.is_expanding:
        key_positives.append("volatility expanding")

    pos_str = ", ".join(key_positives) if key_positives else "no strong positives"
    neg_str = ", ".join(key_negatives) if key_negatives else "no major negatives"

    return (
        f"The market is {regime_desc} with a {direction.value.lower()} bias. "
        f"Swing trading {verdict} (score {dom_score:.0f}/100, {dominant} bias). "
        f"Supporting factors: {pos_str}. "
        f"Risk factors: {neg_str}."
    )
