"""Settings management for Elliott Wave Trading Bot."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    broker_api_key: str = Field(default="", description="Broker API key")
    broker_api_secret: str = Field(default="", description="Broker API secret")

    # Trading Parameters
    starting_capital: float = Field(default=10000.0, description="Starting capital")
    risk_per_trade: float = Field(
        default=2.0, description="Risk per trade as percentage"
    )
    max_positions: int = Field(default=5, description="Maximum concurrent positions")
    default_symbols: str = Field(
        default="AAPL,MSFT,GOOGL,AMZN,TSLA",
        description="Comma-separated list of symbols",
    )
    timeframe: str = Field(default="1h", description="Trading timeframe")

    # Elliott Wave Settings
    min_wave_length: int = Field(
        default=5, description="Minimum wave length in bars"
    )
    fib_tolerance: float = Field(
        default=10.0, description="Fibonacci tolerance percentage"
    )
    wave_lookback: int = Field(
        default=100, description="Wave detection lookback period"
    )

    # Risk Management
    stop_loss_pct: float = Field(default=2.0, description="Stop loss percentage")
    take_profit_pct: float = Field(default=6.0, description="Take profit percentage")
    trailing_stop_pct: float = Field(
        default=3.0, description="Trailing stop activation percentage"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/trading.log", description="Log file path")

    # Mode
    trading_mode: str = Field(
        default="paper", description="Trading mode: paper or live"
    )

    @field_validator("default_symbols", mode="before")
    @classmethod
    def parse_symbols(cls, v: str) -> str:
        """Ensure symbols string is properly formatted."""
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def symbols_list(self) -> List[str]:
        """Get symbols as a list."""
        return [s.strip().upper() for s in self.default_symbols.split(",")]

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """Validate trading mode."""
        allowed = ["paper", "live"]
        if v.lower() not in allowed:
            raise ValueError(f"Trading mode must be one of: {allowed}")
        return v.lower()

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        """Validate timeframe."""
        allowed = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk"]
        if v.lower() not in allowed:
            raise ValueError(f"Timeframe must be one of: {allowed}")
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
