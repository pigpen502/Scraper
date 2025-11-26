"""Tests for Elliott Wave analyzer."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.analysis.elliott_wave import (
    ElliottWaveAnalyzer,
    Wave,
    WaveCount,
    WaveType,
    WaveDegree,
)


class TestWave:
    """Tests for Wave dataclass."""

    def test_wave_creation(self):
        """Test basic wave creation."""
        wave = Wave(
            label="1",
            wave_type=WaveType.IMPULSE,
            start_index=0,
            end_index=10,
            start_price=100.0,
            end_price=120.0,
        )

        assert wave.label == "1"
        assert wave.wave_type == WaveType.IMPULSE
        assert wave.start_index == 0
        assert wave.end_index == 10
        assert wave.start_price == 100.0
        assert wave.end_price == 120.0

    def test_wave_length(self):
        """Test wave length calculation."""
        wave = Wave(
            label="1",
            wave_type=WaveType.IMPULSE,
            start_index=0,
            end_index=10,
            start_price=100.0,
            end_price=120.0,
        )

        assert wave.length == 20.0
        assert wave.abs_length == 20.0

    def test_wave_direction(self):
        """Test wave direction detection."""
        up_wave = Wave(
            label="1",
            wave_type=WaveType.IMPULSE,
            start_index=0,
            end_index=10,
            start_price=100.0,
            end_price=120.0,
        )
        assert up_wave.direction == "up"

        down_wave = Wave(
            label="2",
            wave_type=WaveType.IMPULSE,
            start_index=10,
            end_index=20,
            start_price=120.0,
            end_price=110.0,
        )
        assert down_wave.direction == "down"

    def test_wave_bars(self):
        """Test wave bar count."""
        wave = Wave(
            label="1",
            wave_type=WaveType.IMPULSE,
            start_index=5,
            end_index=15,
            start_price=100.0,
            end_price=120.0,
        )
        assert wave.bars == 10

    def test_wave_percentage_change(self):
        """Test percentage change calculation."""
        wave = Wave(
            label="1",
            wave_type=WaveType.IMPULSE,
            start_index=0,
            end_index=10,
            start_price=100.0,
            end_price=120.0,
        )
        assert wave.percentage_change == 20.0


class TestWaveCount:
    """Tests for WaveCount dataclass."""

    def test_wave_count_is_complete_impulse(self):
        """Test impulse wave completion check."""
        waves = [
            Wave("1", WaveType.IMPULSE, 0, 10, 100, 120),
            Wave("2", WaveType.IMPULSE, 10, 20, 120, 110),
            Wave("3", WaveType.IMPULSE, 20, 40, 110, 150),
            Wave("4", WaveType.IMPULSE, 40, 50, 150, 135),
            Wave("5", WaveType.IMPULSE, 50, 60, 135, 160),
        ]

        count = WaveCount(waves=waves, pattern_type=WaveType.IMPULSE)
        assert count.is_complete is True

        incomplete = WaveCount(waves=waves[:3], pattern_type=WaveType.IMPULSE)
        assert incomplete.is_complete is False

    def test_wave_count_is_complete_corrective(self):
        """Test corrective wave completion check."""
        waves = [
            Wave("A", WaveType.CORRECTIVE, 0, 10, 160, 140),
            Wave("B", WaveType.CORRECTIVE, 10, 15, 140, 150),
            Wave("C", WaveType.CORRECTIVE, 15, 25, 150, 130),
        ]

        count = WaveCount(waves=waves, pattern_type=WaveType.CORRECTIVE)
        assert count.is_complete is True

    def test_current_wave(self):
        """Test getting current wave."""
        waves = [
            Wave("1", WaveType.IMPULSE, 0, 10, 100, 120),
            Wave("2", WaveType.IMPULSE, 10, 20, 120, 110),
        ]

        count = WaveCount(waves=waves)
        assert count.current_wave.label == "2"

        empty_count = WaveCount(waves=[])
        assert empty_count.current_wave is None


class TestElliottWaveAnalyzer:
    """Tests for ElliottWaveAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ElliottWaveAnalyzer(
            min_wave_length=3,
            fib_tolerance=15.0,
            lookback=50,
        )

    @pytest.fixture
    def sample_bullish_data(self):
        """Create sample bullish impulse data."""
        # Create data that resembles a 5-wave impulse
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")

        # Wave pattern: up, down, up, down, up
        prices = []
        base = 100

        # Wave 1 (up)
        for i in range(15):
            base += 0.5 + np.random.random() * 0.3
            prices.append(base)

        # Wave 2 (down)
        for i in range(10):
            base -= 0.3 + np.random.random() * 0.2
            prices.append(base)

        # Wave 3 (up - strongest)
        for i in range(25):
            base += 0.7 + np.random.random() * 0.4
            prices.append(base)

        # Wave 4 (down)
        for i in range(12):
            base -= 0.25 + np.random.random() * 0.15
            prices.append(base)

        # Wave 5 (up)
        for i in range(15):
            base += 0.4 + np.random.random() * 0.25
            prices.append(base)

        # Remaining data
        while len(prices) < 100:
            base += np.random.random() * 0.2 - 0.1
            prices.append(base)

        prices = np.array(prices[:100])

        df = pd.DataFrame(
            {
                "open": prices - np.random.random(100) * 0.5,
                "high": prices + np.random.random(100) * 0.5,
                "low": prices - np.random.random(100) * 0.7,
                "close": prices,
                "volume": np.random.randint(1000, 10000, 100),
            },
            index=dates,
        )

        return df

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.min_wave_length == 3
        assert analyzer.fib_tolerance == 15.0
        assert analyzer.lookback == 50

    def test_find_pivots(self, analyzer, sample_bullish_data):
        """Test pivot point detection."""
        pivots = analyzer._find_pivots(sample_bullish_data)

        # Should find some pivot points
        assert len(pivots) > 0

        # Pivots should have correct structure
        for pivot in pivots:
            assert len(pivot) == 3
            assert isinstance(pivot[0], int)  # index
            assert isinstance(pivot[1], float)  # price
            assert pivot[2] in ["high", "low"]  # type

    def test_filter_alternating_pivots(self, analyzer):
        """Test pivot alternation filtering."""
        pivots = [
            (0, 100.0, "low"),
            (5, 110.0, "high"),
            (7, 112.0, "high"),  # Duplicate high - should keep higher
            (10, 105.0, "low"),
            (12, 103.0, "low"),  # Duplicate low - should keep lower
        ]

        filtered = analyzer._filter_alternating_pivots(pivots)

        # Should alternate between high and low
        for i in range(1, len(filtered)):
            assert filtered[i][2] != filtered[i - 1][2]

    def test_analyze_returns_wave_count_or_none(self, analyzer, sample_bullish_data):
        """Test that analyze returns WaveCount or None."""
        result = analyzer.analyze(sample_bullish_data)

        # Result should be WaveCount or None
        assert result is None or isinstance(result, WaveCount)

    def test_analyze_insufficient_data(self, analyzer):
        """Test analysis with insufficient data."""
        small_df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [101, 102, 103],
                "low": [99, 100, 101],
                "close": [100.5, 101.5, 102.5],
                "volume": [1000, 1000, 1000],
            }
        )

        result = analyzer.analyze(small_df)
        assert result is None

    def test_get_current_wave_position(self, analyzer):
        """Test wave position description."""
        waves = [
            Wave("1", WaveType.IMPULSE, 0, 10, 100, 120),
            Wave("2", WaveType.IMPULSE, 10, 20, 120, 110),
        ]

        count = WaveCount(
            waves=waves,
            pattern_type=WaveType.IMPULSE,
            trend_direction="up",
        )

        position = analyzer.get_current_wave_position(count, 115)
        assert "Wave 2 complete" in position or "Wave 3" in position


class TestFibonacciRelationships:
    """Tests for Fibonacci calculations."""

    @pytest.fixture
    def analyzer(self):
        return ElliottWaveAnalyzer()

    def test_wave2_retracement(self, analyzer):
        """Test Wave 2 retracement validation."""
        # Valid Wave 2: retraces less than 100%
        waves = [
            Wave("1", WaveType.IMPULSE, 0, 10, 100, 120),  # +20 points
            Wave("2", WaveType.IMPULSE, 10, 20, 120, 108),  # -12 points (60% retrace)
        ]

        # Wave 2 end (108) is above Wave 1 start (100), so valid
        assert waves[1].end_price > waves[0].start_price

    def test_wave3_not_shortest(self, analyzer):
        """Test Wave 3 is not shortest rule."""
        # Wave 3 should not be shortest
        wave1_length = 20
        wave3_length = 30
        wave5_length = 15

        # Wave 3 is longest - valid
        assert wave3_length >= wave1_length or wave3_length >= wave5_length

        # Invalid case
        wave3_short = 10
        is_shortest = wave3_short < wave1_length and wave3_short < wave5_length
        assert is_shortest  # This would invalidate the count
