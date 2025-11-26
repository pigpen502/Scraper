"""Pattern detection combining Elliott Wave with technical analysis."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .elliott_wave import ElliottWaveAnalyzer, WaveCount, WaveType
from .indicators import TechnicalIndicators
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PatternConfidence(Enum):
    """Pattern confidence levels."""

    HIGH = "high"  # > 80%
    MEDIUM = "medium"  # 60-80%
    LOW = "low"  # < 60%


@dataclass
class WavePattern:
    """Detected wave pattern with trading signals."""

    symbol: str
    timestamp: datetime
    wave_count: Optional[WaveCount]
    pattern_type: str
    trend: str
    confidence: PatternConfidence
    confidence_score: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    invalidation: Optional[float] = None
    supporting_signals: List[str] = None
    conflicting_signals: List[str] = None
    notes: str = ""

    def __post_init__(self):
        if self.supporting_signals is None:
            self.supporting_signals = []
        if self.conflicting_signals is None:
            self.conflicting_signals = []

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        """Calculate risk/reward ratio for take_profit_1."""
        if self.entry_price and self.stop_loss and self.take_profit_1:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit_1 - self.entry_price)
            return reward / risk if risk > 0 else None
        return None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "pattern_type": self.pattern_type,
            "trend": self.trend,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "invalidation": self.invalidation,
            "risk_reward": self.risk_reward_ratio,
            "supporting_signals": self.supporting_signals,
            "conflicting_signals": self.conflicting_signals,
            "notes": self.notes,
        }


class PatternDetector:
    """
    Detects trading patterns by combining Elliott Wave analysis
    with technical indicators for confirmation.
    """

    def __init__(
        self,
        min_wave_length: int = 5,
        fib_tolerance: float = 10.0,
        lookback: int = 100,
    ):
        """
        Initialize the pattern detector.

        Args:
            min_wave_length: Minimum wave length
            fib_tolerance: Fibonacci tolerance percentage
            lookback: Analysis lookback period
        """
        self.wave_analyzer = ElliottWaveAnalyzer(
            min_wave_length=min_wave_length,
            fib_tolerance=fib_tolerance,
            lookback=lookback,
        )
        self.lookback = lookback

    def detect_pattern(
        self, symbol: str, df: pd.DataFrame
    ) -> Optional[WavePattern]:
        """
        Detect Elliott Wave pattern with technical confirmation.

        Args:
            symbol: Trading symbol
            df: OHLCV DataFrame

        Returns:
            WavePattern if valid pattern found
        """
        if len(df) < self.lookback:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        # Calculate all technical indicators
        df_with_indicators = TechnicalIndicators.calculate_all(df)

        # Analyze Elliott Wave structure
        wave_count = self.wave_analyzer.analyze(df)

        if wave_count is None:
            logger.debug(f"No wave pattern found for {symbol}")
            return None

        # Get technical confirmation signals
        supporting, conflicting = self._get_confirmation_signals(
            df_with_indicators, wave_count
        )

        # Adjust confidence based on confirmations
        adjusted_confidence = self._adjust_confidence(
            wave_count.confidence, supporting, conflicting
        )

        # Determine confidence level
        if adjusted_confidence >= 0.8:
            confidence_level = PatternConfidence.HIGH
        elif adjusted_confidence >= 0.6:
            confidence_level = PatternConfidence.MEDIUM
        else:
            confidence_level = PatternConfidence.LOW

        # Calculate trading levels
        current_price = df["close"].iloc[-1]
        entry, stop, tp1, tp2, tp3 = self._calculate_trading_levels(
            wave_count, current_price, df_with_indicators
        )

        # Create pattern object
        pattern = WavePattern(
            symbol=symbol,
            timestamp=datetime.now(),
            wave_count=wave_count,
            pattern_type=wave_count.pattern_type.value,
            trend=wave_count.trend_direction,
            confidence=confidence_level,
            confidence_score=adjusted_confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            invalidation=wave_count.invalidation_level,
            supporting_signals=supporting,
            conflicting_signals=conflicting,
            notes=self.wave_analyzer.get_current_wave_position(
                wave_count, current_price
            ),
        )

        return pattern

    def _get_confirmation_signals(
        self, df: pd.DataFrame, wave_count: WaveCount
    ) -> Tuple[List[str], List[str]]:
        """
        Get technical signals that support or conflict with wave count.

        Args:
            df: DataFrame with indicators
            wave_count: Elliott Wave count

        Returns:
            Tuple of (supporting_signals, conflicting_signals)
        """
        supporting = []
        conflicting = []

        latest = df.iloc[-1]
        trend = wave_count.trend_direction

        # RSI Analysis
        rsi = latest.get("rsi")
        if rsi is not None:
            if trend == "up":
                if 40 < rsi < 70:
                    supporting.append("RSI supportive (40-70)")
                elif rsi > 80:
                    conflicting.append("RSI overbought")
                elif rsi < 30:
                    supporting.append("RSI oversold - potential Wave 2/4 bottom")
            else:
                if 30 < rsi < 60:
                    supporting.append("RSI supportive (30-60)")
                elif rsi < 20:
                    conflicting.append("RSI oversold")
                elif rsi > 70:
                    supporting.append("RSI overbought - potential Wave 2/B top")

        # MACD Analysis
        macd = latest.get("macd")
        macd_signal = latest.get("macd_signal")
        if macd is not None and macd_signal is not None:
            if trend == "up":
                if macd > macd_signal:
                    supporting.append("MACD bullish crossover")
                else:
                    conflicting.append("MACD bearish")
            else:
                if macd < macd_signal:
                    supporting.append("MACD bearish crossover")
                else:
                    conflicting.append("MACD bullish")

        # Wave Oscillator Analysis
        wave_osc = latest.get("wave_oscillator")
        if wave_osc is not None:
            # Check for divergences
            if len(wave_count.waves) >= 3:
                if abs(wave_osc) > df["wave_oscillator"].iloc[-20:].abs().mean() * 1.5:
                    supporting.append("Strong Wave Oscillator - Wave 3 characteristics")

        # EMA Analysis
        close = latest.get("close")
        ema_21 = latest.get("ema_21")
        ema_50 = latest.get("ema_50")

        if close is not None and ema_21 is not None and ema_50 is not None:
            if trend == "up":
                if close > ema_21 > ema_50:
                    supporting.append("Price above stacked EMAs (bullish)")
                elif close < ema_50:
                    conflicting.append("Price below EMA 50")
            else:
                if close < ema_21 < ema_50:
                    supporting.append("Price below stacked EMAs (bearish)")
                elif close > ema_50:
                    conflicting.append("Price above EMA 50")

        # Bollinger Bands Analysis
        bb_percent = latest.get("bb_percent")
        if bb_percent is not None:
            if trend == "up":
                if 0.2 < bb_percent < 0.8:
                    supporting.append("BB %B in normal range")
                elif bb_percent > 1.0:
                    conflicting.append("Price above upper BB - extended")
            else:
                if 0.2 < bb_percent < 0.8:
                    supporting.append("BB %B in normal range")
                elif bb_percent < 0.0:
                    conflicting.append("Price below lower BB - extended")

        # Stochastic Analysis
        stoch_k = latest.get("stoch_k")
        if stoch_k is not None:
            if trend == "up":
                if 20 < stoch_k < 80:
                    supporting.append("Stochastic not overextended")
                elif stoch_k > 80:
                    conflicting.append("Stochastic overbought")
            else:
                if 20 < stoch_k < 80:
                    supporting.append("Stochastic not overextended")
                elif stoch_k < 20:
                    conflicting.append("Stochastic oversold")

        return supporting, conflicting

    def _adjust_confidence(
        self,
        base_confidence: float,
        supporting: List[str],
        conflicting: List[str],
    ) -> float:
        """Adjust confidence based on technical confirmations."""
        # Each supporting signal adds up to 5%
        support_boost = min(len(supporting) * 0.05, 0.2)

        # Each conflicting signal reduces by up to 10%
        conflict_penalty = min(len(conflicting) * 0.1, 0.3)

        adjusted = base_confidence + support_boost - conflict_penalty
        return max(0.0, min(1.0, adjusted))

    def _calculate_trading_levels(
        self,
        wave_count: WaveCount,
        current_price: float,
        df: pd.DataFrame,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calculate entry, stop loss, and take profit levels.

        Args:
            wave_count: Wave count analysis
            current_price: Current market price
            df: DataFrame with indicators

        Returns:
            Tuple of (entry, stop_loss, tp1, tp2, tp3)
        """
        atr = df["atr"].iloc[-1] if "atr" in df.columns else current_price * 0.02

        if wave_count.pattern_type == WaveType.IMPULSE:
            return self._calculate_impulse_levels(
                wave_count, current_price, atr
            )
        else:
            return self._calculate_corrective_levels(
                wave_count, current_price, atr
            )

    def _calculate_impulse_levels(
        self,
        wave_count: WaveCount,
        current_price: float,
        atr: float,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calculate levels for impulse wave trading."""
        targets = wave_count.target_levels
        invalidation = wave_count.invalidation_level

        if wave_count.trend_direction == "up":
            # Bullish impulse
            entry = current_price
            stop_loss = invalidation if invalidation else current_price - (2 * atr)

            tp1 = targets.get("wave5_100", current_price + (2 * atr))
            tp2 = targets.get("wave5_161.8", current_price + (3 * atr))
            tp3 = targets.get("wave5_261.8", current_price + (4 * atr))

        else:
            # Bearish impulse (short)
            entry = current_price
            stop_loss = invalidation if invalidation else current_price + (2 * atr)

            tp1 = targets.get("wave5_100", current_price - (2 * atr))
            tp2 = targets.get("wave5_161.8", current_price - (3 * atr))
            tp3 = targets.get("wave5_261.8", current_price - (4 * atr))

        return entry, stop_loss, tp1, tp2, tp3

    def _calculate_corrective_levels(
        self,
        wave_count: WaveCount,
        current_price: float,
        atr: float,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calculate levels for corrective wave trading."""
        targets = wave_count.target_levels

        # After correction, expect new impulse in opposite direction
        if wave_count.trend_direction == "down":
            # Correction down, expect up move
            entry = current_price
            stop_loss = current_price - (2 * atr)

            tp1 = targets.get("wave_c_100", current_price + (2 * atr))
            tp2 = targets.get("wave_c_161.8", current_price + (3 * atr))
            tp3 = current_price + (4 * atr)

        else:
            # Correction up, expect down move
            entry = current_price
            stop_loss = current_price + (2 * atr)

            tp1 = targets.get("wave_c_100", current_price - (2 * atr))
            tp2 = targets.get("wave_c_161.8", current_price - (3 * atr))
            tp3 = current_price - (4 * atr)

        return entry, stop_loss, tp1, tp2, tp3

    def scan_multiple(
        self, data: Dict[str, pd.DataFrame], min_confidence: float = 0.5
    ) -> List[WavePattern]:
        """
        Scan multiple symbols for patterns.

        Args:
            data: Dictionary of symbol -> DataFrame
            min_confidence: Minimum confidence score

        Returns:
            List of detected patterns sorted by confidence
        """
        patterns = []

        for symbol, df in data.items():
            try:
                pattern = self.detect_pattern(symbol, df)
                if pattern and pattern.confidence_score >= min_confidence:
                    patterns.append(pattern)
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

        # Sort by confidence score descending
        patterns.sort(key=lambda x: x.confidence_score, reverse=True)

        return patterns
