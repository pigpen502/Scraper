"""Tests for signal generation."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.bot.signals import (
    Signal,
    SignalType,
    SignalStrength,
    SignalGenerator,
)
from src.analysis.elliott_wave import WaveCount, WaveType, Wave


class TestSignal:
    """Tests for Signal dataclass."""

    def test_signal_creation(self):
        """Test basic signal creation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.entry_price == 150.0
        assert signal.stop_loss == 145.0
        assert signal.take_profit_1 == 165.0

    def test_risk_amount(self):
        """Test risk calculation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert signal.risk_amount == 5.0

    def test_reward_amount(self):
        """Test reward calculation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert signal.reward_amount == 15.0

    def test_risk_reward_ratio(self):
        """Test risk/reward ratio calculation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert signal.risk_reward_ratio == 3.0  # 15/5

    def test_to_dict(self):
        """Test dictionary conversion."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
            confidence=0.85,
        )

        d = signal.to_dict()

        assert d["symbol"] == "AAPL"
        assert d["type"] == "buy"
        assert d["strength"] == "strong"
        assert d["entry"] == 150.0
        assert d["stop_loss"] == 145.0
        assert d["take_profit_1"] == 165.0
        assert d["confidence"] == 0.85


class TestSignalGenerator:
    """Tests for SignalGenerator."""

    @pytest.fixture
    def generator(self):
        """Create signal generator instance."""
        return SignalGenerator(
            min_confidence=0.5,
            min_risk_reward=1.5,
        )

    @pytest.fixture
    def sample_data(self):
        """Create sample price data."""
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", periods=150, freq="D")

        # Create trending data
        trend = np.linspace(100, 130, 150)
        noise = np.random.normal(0, 2, 150)
        prices = trend + noise

        df = pd.DataFrame(
            {
                "open": prices - np.random.random(150),
                "high": prices + np.random.random(150) * 2,
                "low": prices - np.random.random(150) * 2,
                "close": prices,
                "volume": np.random.randint(1000000, 5000000, 150),
            },
            index=dates,
        )

        return df

    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator.min_confidence == 0.5
        assert generator.min_risk_reward == 1.5

    def test_generate_signal_returns_signal_or_none(self, generator, sample_data):
        """Test that generate_signal returns Signal or None."""
        result = generator.generate_signal("TEST", sample_data)

        assert result is None or isinstance(result, Signal)

    def test_validate_signal_valid(self, generator):
        """Test signal validation - valid signal."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
            invalidation_price=140.0,
        )

        # Price within acceptable range
        assert generator.validate_signal(signal, 151.0) is True

    def test_validate_signal_invalid_price_moved(self, generator):
        """Test signal validation - price moved too far."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        # Price moved more than 5%
        assert generator.validate_signal(signal, 160.0) is False

    def test_validate_signal_invalidated(self, generator):
        """Test signal validation - invalidation level hit."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
            invalidation_price=140.0,
        )

        # Price below invalidation for buy signal
        assert generator.validate_signal(signal, 138.0) is False


class TestSignalTypes:
    """Tests for signal type enum."""

    def test_signal_types_exist(self):
        """Test all signal types exist."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
        assert SignalType.CLOSE_LONG.value == "close_long"
        assert SignalType.CLOSE_SHORT.value == "close_short"

    def test_signal_strength_exist(self):
        """Test all signal strengths exist."""
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.MODERATE.value == "moderate"
        assert SignalStrength.WEAK.value == "weak"
