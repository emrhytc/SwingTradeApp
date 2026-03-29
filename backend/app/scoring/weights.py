"""
Scoring weights and threshold configuration.
All values are configurable without changing any scoring logic.
"""
from dataclasses import dataclass
from app.config import settings


@dataclass(frozen=True)
class ScoringWeights:
    trend: float = settings.WEIGHT_TREND
    volatility: float = settings.WEIGHT_VOLATILITY
    chop: float = settings.WEIGHT_CHOP
    participation: float = settings.WEIGHT_PARTICIPATION
    mtf: float = settings.WEIGHT_MTF
    context: float = settings.WEIGHT_CONTEXT

    def validate(self) -> None:
        total = sum([
            self.trend, self.volatility, self.chop,
            self.participation, self.mtf, self.context
        ])
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.4f}")


# Singleton — used throughout the scoring pipeline
DEFAULT_WEIGHTS = ScoringWeights()


@dataclass(frozen=True)
class DecisionThresholds:
    suitable: float = settings.THRESHOLD_SUITABLE
    cautious: float = settings.THRESHOLD_CAUTIOUS


DEFAULT_THRESHOLDS = DecisionThresholds()
