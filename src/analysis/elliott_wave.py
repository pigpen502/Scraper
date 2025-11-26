"""Elliott Wave Theory implementation for pattern detection and analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..utils.helpers import (
    calculate_percentage_change,
    fibonacci_extension_levels,
    fibonacci_retracement_levels,
    find_local_extrema,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WaveType(Enum):
    """Types of Elliott Waves."""

    IMPULSE = "impulse"  # 5-wave pattern in trend direction
    CORRECTIVE = "corrective"  # 3-wave pattern against trend
    DIAGONAL = "diagonal"  # Leading or ending diagonal
    TRIANGLE = "triangle"  # Corrective triangle pattern


class WaveDegree(Enum):
    """Elliott Wave degrees (time frames)."""

    GRAND_SUPERCYCLE = "Grand Supercycle"
    SUPERCYCLE = "Supercycle"
    CYCLE = "Cycle"
    PRIMARY = "Primary"
    INTERMEDIATE = "Intermediate"
    MINOR = "Minor"
    MINUTE = "Minute"
    MINUETTE = "Minuette"
    SUBMINUETTE = "Subminuette"


@dataclass
class Wave:
    """Represents a single Elliott Wave."""

    label: str  # 1, 2, 3, 4, 5 or A, B, C
    wave_type: WaveType
    start_index: int
    end_index: int
    start_price: float
    end_price: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def length(self) -> float:
        """Price movement of the wave."""
        return self.end_price - self.start_price

    @property
    def abs_length(self) -> float:
        """Absolute price movement."""
        return abs(self.length)

    @property
    def direction(self) -> str:
        """Wave direction: 'up' or 'down'."""
        return "up" if self.end_price > self.start_price else "down"

    @property
    def bars(self) -> int:
        """Number of bars in the wave."""
        return self.end_index - self.start_index

    @property
    def percentage_change(self) -> float:
        """Percentage change of the wave."""
        return calculate_percentage_change(self.start_price, self.end_price)


@dataclass
class WaveCount:
    """Complete wave count analysis."""

    waves: List[Wave] = field(default_factory=list)
    pattern_type: WaveType = WaveType.IMPULSE
    trend_direction: str = "up"
    degree: WaveDegree = WaveDegree.MINOR
    confidence: float = 0.0
    fibonacci_ratios: Dict[str, float] = field(default_factory=dict)
    invalidation_level: Optional[float] = None
    target_levels: Dict[str, float] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if wave count is complete."""
        if self.pattern_type == WaveType.IMPULSE:
            return len(self.waves) == 5
        elif self.pattern_type == WaveType.CORRECTIVE:
            return len(self.waves) == 3
        return False

    @property
    def current_wave(self) -> Optional[Wave]:
        """Get the most recent wave."""
        return self.waves[-1] if self.waves else None


class ElliottWaveAnalyzer:
    """
    Analyzes price data to identify Elliott Wave patterns.

    Elliott Wave Theory Rules:
    1. Wave 2 never retraces more than 100% of Wave 1
    2. Wave 3 is never the shortest among waves 1, 3, and 5
    3. Wave 4 never enters the price territory of Wave 1 (in impulse waves)

    Common Fibonacci Relationships:
    - Wave 2: 50%, 61.8%, or 78.6% retracement of Wave 1
    - Wave 3: 161.8%, 200%, or 261.8% extension of Wave 1
    - Wave 4: 38.2% or 50% retracement of Wave 3
    - Wave 5: Equal to Wave 1, or 61.8% of Wave 1-3
    """

    def __init__(
        self,
        min_wave_length: int = 5,
        fib_tolerance: float = 10.0,
        lookback: int = 100,
    ):
        """
        Initialize the Elliott Wave Analyzer.

        Args:
            min_wave_length: Minimum bars for a wave
            fib_tolerance: Tolerance for Fibonacci ratios (percentage)
            lookback: Number of bars to analyze
        """
        self.min_wave_length = min_wave_length
        self.fib_tolerance = fib_tolerance
        self.lookback = lookback

    def analyze(self, df: pd.DataFrame) -> Optional[WaveCount]:
        """
        Analyze price data for Elliott Wave patterns.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            WaveCount object or None if no pattern found
        """
        if len(df) < self.lookback:
            logger.warning(f"Insufficient data: {len(df)} bars (need {self.lookback})")
            return None

        # Use most recent data
        df = df.tail(self.lookback).copy()

        # Find pivot points (local extrema)
        pivots = self._find_pivots(df)

        if len(pivots) < 6:  # Need at least 6 pivots for a 5-wave pattern
            logger.debug("Insufficient pivot points found")
            return None

        # Try to identify impulse wave pattern
        impulse_count = self._identify_impulse_wave(df, pivots)
        if impulse_count and impulse_count.confidence > 0.5:
            return impulse_count

        # Try to identify corrective wave pattern
        corrective_count = self._identify_corrective_wave(df, pivots)
        if corrective_count and corrective_count.confidence > 0.5:
            return corrective_count

        return None

    def _find_pivots(self, df: pd.DataFrame) -> List[Tuple[int, float, str]]:
        """
        Find pivot points (swing highs and lows).

        Args:
            df: Price DataFrame

        Returns:
            List of (index, price, type) tuples
        """
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        pivots = []
        order = max(3, self.min_wave_length // 2)

        # Find local maxima and minima
        for i in range(order, len(df) - order):
            # Check for swing high
            is_swing_high = True
            for j in range(1, order + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break

            if is_swing_high:
                pivots.append((i, highs[i], "high"))

            # Check for swing low
            is_swing_low = True
            for j in range(1, order + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break

            if is_swing_low:
                pivots.append((i, lows[i], "low"))

        # Sort by index
        pivots.sort(key=lambda x: x[0])

        # Filter alternating pivots
        filtered = self._filter_alternating_pivots(pivots)

        return filtered

    def _filter_alternating_pivots(
        self, pivots: List[Tuple[int, float, str]]
    ) -> List[Tuple[int, float, str]]:
        """Ensure pivots alternate between highs and lows."""
        if len(pivots) < 2:
            return pivots

        filtered = [pivots[0]]

        for pivot in pivots[1:]:
            if pivot[2] != filtered[-1][2]:
                filtered.append(pivot)
            else:
                # Same type - keep the more extreme one
                if pivot[2] == "high" and pivot[1] > filtered[-1][1]:
                    filtered[-1] = pivot
                elif pivot[2] == "low" and pivot[1] < filtered[-1][1]:
                    filtered[-1] = pivot

        return filtered

    def _identify_impulse_wave(
        self, df: pd.DataFrame, pivots: List[Tuple[int, float, str]]
    ) -> Optional[WaveCount]:
        """
        Identify 5-wave impulse pattern.

        Args:
            df: Price DataFrame
            pivots: List of pivot points

        Returns:
            WaveCount if valid impulse found
        """
        if len(pivots) < 6:
            return None

        best_count = None
        best_confidence = 0.0

        # Try different starting points
        for start_idx in range(len(pivots) - 5):
            wave_pivots = pivots[start_idx : start_idx + 6]

            # Determine trend direction
            if wave_pivots[0][2] == "low":
                trend = "up"
            else:
                trend = "down"

            # Validate wave structure
            waves, confidence = self._validate_impulse_structure(
                df, wave_pivots, trend
            )

            if waves and confidence > best_confidence:
                best_confidence = confidence
                best_count = WaveCount(
                    waves=waves,
                    pattern_type=WaveType.IMPULSE,
                    trend_direction=trend,
                    confidence=confidence,
                )

        if best_count:
            # Calculate targets and invalidation
            self._calculate_targets(best_count)
            self._calculate_invalidation(best_count)

        return best_count

    def _validate_impulse_structure(
        self,
        df: pd.DataFrame,
        pivots: List[Tuple[int, float, str]],
        trend: str,
    ) -> Tuple[Optional[List[Wave]], float]:
        """
        Validate that pivots form a valid impulse wave.

        Elliott Wave Rules for Impulse:
        1. Wave 2 never retraces more than 100% of Wave 1
        2. Wave 3 is never the shortest
        3. Wave 4 never enters Wave 1 territory
        """
        if len(pivots) < 6:
            return None, 0.0

        confidence = 1.0
        waves = []

        # Create wave objects
        for i in range(5):
            label = str(i + 1)
            wave = Wave(
                label=label,
                wave_type=WaveType.IMPULSE,
                start_index=pivots[i][0],
                end_index=pivots[i + 1][0],
                start_price=pivots[i][1],
                end_price=pivots[i + 1][1],
            )
            waves.append(wave)

        # Rule 1: Wave 2 cannot retrace more than 100% of Wave 1
        if trend == "up":
            if waves[1].end_price < waves[0].start_price:
                return None, 0.0
        else:
            if waves[1].end_price > waves[0].start_price:
                return None, 0.0

        # Rule 2: Wave 3 cannot be the shortest
        wave1_length = waves[0].abs_length
        wave3_length = waves[2].abs_length
        wave5_length = waves[4].abs_length

        if wave3_length < wave1_length and wave3_length < wave5_length:
            return None, 0.0

        # Rule 3: Wave 4 cannot overlap Wave 1 (for impulse waves)
        if trend == "up":
            if waves[3].end_price < waves[0].end_price:
                confidence *= 0.5  # Reduce confidence instead of rejection
        else:
            if waves[3].end_price > waves[0].end_price:
                confidence *= 0.5

        # Check Fibonacci relationships
        fib_score = self._check_fibonacci_relationships(waves, trend)
        confidence *= fib_score

        # Check wave proportions
        proportion_score = self._check_wave_proportions(waves)
        confidence *= proportion_score

        return waves, confidence

    def _check_fibonacci_relationships(
        self, waves: List[Wave], trend: str
    ) -> float:
        """Check Fibonacci retracement/extension relationships."""
        score = 1.0

        # Wave 2 should retrace 50%, 61.8%, or 78.6% of Wave 1
        wave1_length = waves[0].abs_length
        wave2_retrace = waves[1].abs_length / wave1_length if wave1_length > 0 else 0

        ideal_w2_ratios = [0.382, 0.5, 0.618, 0.786]
        w2_score = min(
            abs(wave2_retrace - r) / r for r in ideal_w2_ratios if r > 0
        )
        if w2_score > self.fib_tolerance / 100:
            score *= 0.8

        # Wave 3 should be 161.8%, 200%, or 261.8% of Wave 1
        wave3_extension = waves[2].abs_length / wave1_length if wave1_length > 0 else 0

        ideal_w3_ratios = [1.0, 1.618, 2.0, 2.618]
        w3_score = min(
            abs(wave3_extension - r) / r for r in ideal_w3_ratios if r > 0
        )
        if w3_score > self.fib_tolerance / 100:
            score *= 0.8

        # Wave 4 should retrace 38.2% or 50% of Wave 3
        wave3_length = waves[2].abs_length
        wave4_retrace = waves[3].abs_length / wave3_length if wave3_length > 0 else 0

        ideal_w4_ratios = [0.236, 0.382, 0.5]
        w4_score = min(
            abs(wave4_retrace - r) / r for r in ideal_w4_ratios if r > 0
        )
        if w4_score > self.fib_tolerance / 100:
            score *= 0.8

        return max(score, 0.3)

    def _check_wave_proportions(self, waves: List[Wave]) -> float:
        """Check time/price proportions between waves."""
        score = 1.0

        # Wave 3 typically has the most bars
        if waves[2].bars < waves[0].bars and waves[2].bars < waves[4].bars:
            score *= 0.9

        # Wave 4 typically takes more time than Wave 2
        if waves[3].bars < waves[1].bars * 0.5:
            score *= 0.95

        return score

    def _identify_corrective_wave(
        self, df: pd.DataFrame, pivots: List[Tuple[int, float, str]]
    ) -> Optional[WaveCount]:
        """
        Identify 3-wave corrective pattern (A-B-C).

        Args:
            df: Price DataFrame
            pivots: List of pivot points

        Returns:
            WaveCount if valid correction found
        """
        if len(pivots) < 4:
            return None

        best_count = None
        best_confidence = 0.0

        for start_idx in range(len(pivots) - 3):
            wave_pivots = pivots[start_idx : start_idx + 4]

            # Determine correction direction
            if wave_pivots[0][2] == "high":
                direction = "down"
            else:
                direction = "up"

            waves, confidence = self._validate_corrective_structure(
                df, wave_pivots, direction
            )

            if waves and confidence > best_confidence:
                best_confidence = confidence
                best_count = WaveCount(
                    waves=waves,
                    pattern_type=WaveType.CORRECTIVE,
                    trend_direction=direction,
                    confidence=confidence,
                )

        if best_count:
            self._calculate_targets(best_count)

        return best_count

    def _validate_corrective_structure(
        self,
        df: pd.DataFrame,
        pivots: List[Tuple[int, float, str]],
        direction: str,
    ) -> Tuple[Optional[List[Wave]], float]:
        """Validate ABC corrective structure."""
        if len(pivots) < 4:
            return None, 0.0

        confidence = 1.0
        labels = ["A", "B", "C"]
        waves = []

        for i in range(3):
            wave = Wave(
                label=labels[i],
                wave_type=WaveType.CORRECTIVE,
                start_index=pivots[i][0],
                end_index=pivots[i + 1][0],
                start_price=pivots[i][1],
                end_price=pivots[i + 1][1],
            )
            waves.append(wave)

        # Wave B should not exceed Wave A start
        if direction == "down":
            if waves[1].end_price > waves[0].start_price:
                confidence *= 0.5
        else:
            if waves[1].end_price < waves[0].start_price:
                confidence *= 0.5

        # Check Fibonacci relationships for corrections
        wave_a_length = waves[0].abs_length
        wave_b_retrace = waves[1].abs_length / wave_a_length if wave_a_length > 0 else 0

        # Wave B typically retraces 50-78.6% of Wave A
        if not (0.382 <= wave_b_retrace <= 0.886):
            confidence *= 0.8

        # Wave C often equals Wave A or is 61.8%/161.8% of Wave A
        wave_c_ratio = waves[2].abs_length / wave_a_length if wave_a_length > 0 else 0
        ideal_c_ratios = [0.618, 1.0, 1.272, 1.618]
        c_score = min(abs(wave_c_ratio - r) for r in ideal_c_ratios)
        if c_score > 0.3:
            confidence *= 0.8

        return waves, confidence

    def _calculate_targets(self, wave_count: WaveCount) -> None:
        """Calculate price targets based on wave count."""
        if not wave_count.waves:
            return

        targets = {}

        if wave_count.pattern_type == WaveType.IMPULSE:
            if len(wave_count.waves) >= 4:
                # Calculate Wave 5 targets
                wave1 = wave_count.waves[0]
                wave4 = wave_count.waves[3]

                extensions = fibonacci_extension_levels(
                    wave1.start_price, wave1.end_price, wave4.end_price
                )

                targets["wave5_100"] = extensions["1.0"]
                targets["wave5_161.8"] = extensions["1.618"]
                targets["wave5_261.8"] = extensions["2.618"]

        elif wave_count.pattern_type == WaveType.CORRECTIVE:
            if len(wave_count.waves) >= 2:
                wave_a = wave_count.waves[0]
                wave_b = wave_count.waves[1]

                extensions = fibonacci_extension_levels(
                    wave_a.start_price, wave_a.end_price, wave_b.end_price
                )

                targets["wave_c_100"] = extensions["1.0"]
                targets["wave_c_161.8"] = extensions["1.618"]

        wave_count.target_levels = targets

    def _calculate_invalidation(self, wave_count: WaveCount) -> None:
        """Calculate invalidation level for the wave count."""
        if not wave_count.waves:
            return

        if wave_count.pattern_type == WaveType.IMPULSE:
            # Invalidation for bullish impulse: Wave 4 going below Wave 1 end
            if wave_count.trend_direction == "up":
                wave_count.invalidation_level = wave_count.waves[0].end_price
            else:
                wave_count.invalidation_level = wave_count.waves[0].end_price

    def get_current_wave_position(
        self, wave_count: WaveCount, current_price: float
    ) -> str:
        """
        Determine where price is relative to the wave count.

        Args:
            wave_count: Current wave count
            current_price: Current market price

        Returns:
            Description of current position
        """
        if not wave_count.waves:
            return "No wave count available"

        last_wave = wave_count.waves[-1]

        if wave_count.pattern_type == WaveType.IMPULSE:
            if len(wave_count.waves) == 5:
                return "Wave 5 complete - expect correction"
            elif len(wave_count.waves) == 4:
                return f"In Wave 5 - targets: {wave_count.target_levels}"
            elif len(wave_count.waves) == 3:
                return "Wave 3 complete - expect Wave 4 correction"
            elif len(wave_count.waves) == 2:
                return "Wave 2 complete - Wave 3 starting"
            else:
                return "Wave 1 complete - expect Wave 2 correction"

        elif wave_count.pattern_type == WaveType.CORRECTIVE:
            if len(wave_count.waves) == 3:
                return "ABC correction complete - expect new impulse"
            elif len(wave_count.waves) == 2:
                return "Wave B complete - Wave C in progress"
            else:
                return "Wave A complete - expect Wave B bounce"

        return "Unknown position"
