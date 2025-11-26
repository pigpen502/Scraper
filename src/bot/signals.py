"""Signal generation for Elliott Wave Trading Bot."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd

from ..analysis.elliott_wave import WaveCount, WaveType
from ..analysis.pattern_detector import PatternDetector, WavePattern, PatternConfidence
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    """Trading signal types."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class SignalStrength(Enum):
    """Signal strength levels."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class Signal:
    """Trading signal with all relevant information."""

    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    timestamp: datetime = None
    wave_position: str = ""
    confidence: float = 0.0
    reasons: List[str] = None
    invalidation_price: Optional[float] = None
    pattern: Optional[WavePattern] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.reasons is None:
            self.reasons = []

    @property
    def risk_amount(self) -> float:
        """Calculate risk amount per share."""
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward_amount(self) -> float:
        """Calculate reward amount per share (to TP1)."""
        return abs(self.take_profit_1 - self.entry_price)

    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio."""
        if self.risk_amount == 0:
            return 0
        return self.reward_amount / self.risk_amount

    def to_dict(self) -> Dict:
        """Convert signal to dictionary."""
        return {
            "symbol": self.symbol,
            "type": self.signal_type.value,
            "strength": self.strength.value,
            "entry": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "timestamp": self.timestamp.isoformat(),
            "wave_position": self.wave_position,
            "confidence": self.confidence,
            "risk_reward": self.risk_reward_ratio,
            "reasons": self.reasons,
        }


class SignalGenerator:
    """
    Generates trading signals based on Elliott Wave patterns
    and technical analysis confirmation.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        min_risk_reward: float = 2.0,
        min_wave_length: int = 5,
        fib_tolerance: float = 10.0,
        lookback: int = 100,
    ):
        """
        Initialize the signal generator.

        Args:
            min_confidence: Minimum confidence score for signals
            min_risk_reward: Minimum risk/reward ratio
            min_wave_length: Minimum wave length in bars
            fib_tolerance: Fibonacci tolerance percentage
            lookback: Analysis lookback period
        """
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.pattern_detector = PatternDetector(
            min_wave_length=min_wave_length,
            fib_tolerance=fib_tolerance,
            lookback=lookback,
        )

    def generate_signal(
        self, symbol: str, df: pd.DataFrame
    ) -> Optional[Signal]:
        """
        Generate trading signal for a symbol.

        Args:
            symbol: Trading symbol
            df: OHLCV DataFrame

        Returns:
            Signal object or None
        """
        # Detect pattern
        pattern = self.pattern_detector.detect_pattern(symbol, df)

        if pattern is None:
            return None

        # Check minimum confidence
        if pattern.confidence_score < self.min_confidence:
            logger.debug(
                f"Pattern confidence too low for {symbol}: {pattern.confidence_score:.2f}"
            )
            return None

        # Determine signal type and validate
        signal = self._create_signal(pattern, df)

        if signal is None:
            return None

        # Check risk/reward ratio
        if signal.risk_reward_ratio < self.min_risk_reward:
            logger.debug(
                f"Risk/reward too low for {symbol}: {signal.risk_reward_ratio:.2f}"
            )
            return None

        logger.info(
            f"Generated {signal.signal_type.value} signal for {symbol} "
            f"(confidence: {signal.confidence:.2f}, R:R: {signal.risk_reward_ratio:.2f})"
        )

        return signal

    def _create_signal(
        self, pattern: WavePattern, df: pd.DataFrame
    ) -> Optional[Signal]:
        """
        Create a signal from a detected pattern.

        Args:
            pattern: Detected wave pattern
            df: Price DataFrame

        Returns:
            Signal object or None
        """
        wave_count = pattern.wave_count

        if wave_count is None:
            return None

        # Determine signal type based on wave position
        signal_type = self._determine_signal_type(wave_count, pattern.trend)

        if signal_type == SignalType.HOLD:
            return None

        # Determine signal strength
        strength = self._determine_strength(pattern)

        # Build reasons list
        reasons = self._build_reasons(pattern)

        signal = Signal(
            symbol=pattern.symbol,
            signal_type=signal_type,
            strength=strength,
            entry_price=pattern.entry_price or df["close"].iloc[-1],
            stop_loss=pattern.stop_loss or 0,
            take_profit_1=pattern.take_profit_1 or 0,
            take_profit_2=pattern.take_profit_2,
            take_profit_3=pattern.take_profit_3,
            wave_position=pattern.notes,
            confidence=pattern.confidence_score,
            reasons=reasons,
            invalidation_price=pattern.invalidation,
            pattern=pattern,
        )

        return signal

    def _determine_signal_type(
        self, wave_count: WaveCount, trend: str
    ) -> SignalType:
        """
        Determine signal type based on wave count and position.

        Entry points:
        - End of Wave 2: Buy for Wave 3
        - End of Wave 4: Buy for Wave 5
        - End of ABC correction: Buy for new impulse

        Exit points:
        - End of Wave 3: Partial profit
        - End of Wave 5: Full exit
        """
        num_waves = len(wave_count.waves)

        if wave_count.pattern_type == WaveType.IMPULSE:
            if trend == "up":
                # Bullish impulse
                if num_waves == 2:
                    # Wave 2 complete - buy for Wave 3
                    return SignalType.BUY
                elif num_waves == 4:
                    # Wave 4 complete - buy for Wave 5
                    return SignalType.BUY
                elif num_waves == 5:
                    # Wave 5 complete - take profit / sell
                    return SignalType.CLOSE_LONG
                elif num_waves == 3:
                    # Wave 3 in progress or complete - hold
                    return SignalType.HOLD
            else:
                # Bearish impulse
                if num_waves == 2:
                    return SignalType.SELL
                elif num_waves == 4:
                    return SignalType.SELL
                elif num_waves == 5:
                    return SignalType.CLOSE_SHORT
                elif num_waves == 3:
                    return SignalType.HOLD

        elif wave_count.pattern_type == WaveType.CORRECTIVE:
            if num_waves == 3:
                # ABC correction complete
                if trend == "down":
                    # Correction down complete - buy
                    return SignalType.BUY
                else:
                    # Correction up complete - sell
                    return SignalType.SELL

        return SignalType.HOLD

    def _determine_strength(self, pattern: WavePattern) -> SignalStrength:
        """Determine signal strength from pattern."""
        if pattern.confidence == PatternConfidence.HIGH:
            return SignalStrength.STRONG
        elif pattern.confidence == PatternConfidence.MEDIUM:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _build_reasons(self, pattern: WavePattern) -> List[str]:
        """Build list of reasons for the signal."""
        reasons = []

        # Wave position
        reasons.append(f"Wave Position: {pattern.notes}")

        # Trend
        reasons.append(f"Trend: {pattern.trend}")

        # Pattern type
        reasons.append(f"Pattern: {pattern.pattern_type}")

        # Supporting signals
        if pattern.supporting_signals:
            for signal in pattern.supporting_signals[:3]:
                reasons.append(f"+ {signal}")

        # Conflicting signals (as warnings)
        if pattern.conflicting_signals:
            for signal in pattern.conflicting_signals[:2]:
                reasons.append(f"! {signal}")

        return reasons

    def scan_for_signals(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Signal]:
        """
        Scan multiple symbols for trading signals.

        Args:
            data: Dictionary of symbol -> DataFrame

        Returns:
            List of signals sorted by strength and confidence
        """
        signals = []

        for symbol, df in data.items():
            try:
                signal = self.generate_signal(symbol, df)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")

        # Sort by confidence descending
        signals.sort(key=lambda x: (x.strength.value, x.confidence), reverse=True)

        return signals

    def validate_signal(self, signal: Signal, current_price: float) -> bool:
        """
        Validate if a signal is still valid.

        Args:
            signal: Signal to validate
            current_price: Current market price

        Returns:
            True if signal is still valid
        """
        # Check invalidation level
        if signal.invalidation_price:
            if signal.signal_type == SignalType.BUY:
                if current_price < signal.invalidation_price:
                    logger.info(f"Signal invalidated for {signal.symbol}")
                    return False
            elif signal.signal_type == SignalType.SELL:
                if current_price > signal.invalidation_price:
                    logger.info(f"Signal invalidated for {signal.symbol}")
                    return False

        # Check if price moved too far from entry
        price_diff_pct = abs(current_price - signal.entry_price) / signal.entry_price
        if price_diff_pct > 0.05:  # 5% threshold
            logger.info(f"Signal expired - price moved too far for {signal.symbol}")
            return False

        return True
