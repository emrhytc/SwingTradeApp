from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CACHE_TTL_SECONDS: int = 300
    DEFAULT_DATA_PROVIDER: str = "yfinance"
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/swingtrader.db"
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    # Set to "true" in production to allow all origins (useful before you know the frontend URL)
    CORS_ALLOW_ALL: str = "false"

    # Scoring weights — must sum to 1.0
    WEIGHT_TREND: float = 0.25
    WEIGHT_VOLATILITY: float = 0.20
    WEIGHT_CHOP: float = 0.20
    WEIGHT_PARTICIPATION: float = 0.15
    WEIGHT_MTF: float = 0.15
    WEIGHT_CONTEXT: float = 0.05

    # Decision thresholds
    THRESHOLD_SUITABLE: float = 80.0
    THRESHOLD_CAUTIOUS: float = 60.0

    # Indicator periods
    ADX_PERIOD: int = 14
    ATR_PERIOD: int = 14
    EMA_PERIODS: List[int] = [20, 50, 100, 200]
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    OBV_SLOPE_PERIOD: int = 10
    EFFICIENCY_RATIO_PERIOD: int = 10
    CHOP_PERIOD: int = 14
    VOLUME_AVG_PERIOD: int = 20
    ATR_PERCENTILE_LOOKBACK: int = 252
    SWING_LOOKBACK: int = 20

    def get_cors_origins(self) -> List[str]:
        if self.CORS_ALLOW_ALL.lower() == "true":
            return ["*"]
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
