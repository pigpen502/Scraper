"""Tests for position management."""

import pytest
import tempfile
from pathlib import Path

from src.bot.position_manager import (
    Position,
    PositionManager,
    PositionStatus,
    PositionSide,
)
from src.bot.signals import Signal, SignalType, SignalStrength


class TestPosition:
    """Tests for Position dataclass."""

    def test_position_creation(self):
        """Test basic position creation."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert position.id == "test_1"
        assert position.symbol == "AAPL"
        assert position.side == PositionSide.LONG
        assert position.entry_price == 150.0
        assert position.quantity == 10.0

    def test_current_value(self):
        """Test position value calculation."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert position.current_value == 1500.0

    def test_calculate_pnl_long(self):
        """Test P&L calculation for long position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        # Profit scenario
        assert position.calculate_pnl(160.0) == 100.0  # (160-150) * 10

        # Loss scenario
        assert position.calculate_pnl(145.0) == -50.0  # (145-150) * 10

    def test_calculate_pnl_short(self):
        """Test P&L calculation for short position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.SHORT,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=155.0,
            take_profit_1=135.0,
        )

        # Profit scenario (price goes down)
        assert position.calculate_pnl(140.0) == 100.0  # (150-140) * 10

        # Loss scenario (price goes up)
        assert position.calculate_pnl(155.0) == -50.0  # (150-155) * 10

    def test_should_stop_out_long(self):
        """Test stop loss trigger for long position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        assert position.should_stop_out(144.0) is True
        assert position.should_stop_out(145.0) is True
        assert position.should_stop_out(146.0) is False

    def test_should_stop_out_short(self):
        """Test stop loss trigger for short position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.SHORT,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=155.0,
            take_profit_1=135.0,
        )

        assert position.should_stop_out(156.0) is True
        assert position.should_stop_out(155.0) is True
        assert position.should_stop_out(154.0) is False

    def test_should_take_profit_long(self):
        """Test take profit triggers for long position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=160.0,
            take_profit_2=170.0,
            take_profit_3=180.0,
        )

        assert position.should_take_profit(155.0) == 0  # No TP hit
        assert position.should_take_profit(160.0) == 1  # TP1 hit
        assert position.should_take_profit(170.0) == 2  # TP2 hit
        assert position.should_take_profit(180.0) == 3  # TP3 hit

    def test_update_trailing_stop_long(self):
        """Test trailing stop update for long position."""
        position = Position(
            id="test_1",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=10.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        # Initial trailing stop update
        result = position.update_trailing_stop(160.0, trailing_pct=3.0)
        assert result is True
        assert position.trailing_stop == 160.0 - (160.0 * 0.03)

        # Price moves higher - trailing stop should move up
        old_stop = position.trailing_stop
        position.update_trailing_stop(170.0, trailing_pct=3.0)
        assert position.trailing_stop > old_stop


class TestPositionManager:
    """Tests for PositionManager."""

    @pytest.fixture
    def manager(self):
        """Create position manager with temp state file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            state_file = f.name

        return PositionManager(
            capital=10000.0,
            risk_per_trade=2.0,
            max_positions=3,
            state_file=state_file,
        )

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.capital == 10000.0
        assert manager.risk_per_trade == 2.0
        assert manager.max_positions == 3
        assert len(manager.positions) == 0

    def test_calculate_position_size(self, manager):
        """Test position sizing calculation."""
        # Risk 2% of 10000 = 200
        # Stop distance = 5
        # Position size = 200 / 5 = 40 shares
        size = manager.calculate_position_size(
            entry_price=100.0,
            stop_loss=95.0,
        )

        assert size == 40.0

    def test_calculate_position_size_capped(self, manager):
        """Test position size is capped at 25% of capital."""
        # Very small stop would create huge position
        # Should be capped at 25% of capital
        size = manager.calculate_position_size(
            entry_price=100.0,
            stop_loss=99.9,  # 0.1 stop distance
        )

        max_shares = (manager.capital * 0.25) / 100.0
        assert size <= max_shares

    def test_can_open_position(self, manager):
        """Test position opening rules."""
        # Should be able to open position initially
        assert manager.can_open_position("AAPL") is True

    def test_can_open_position_max_reached(self, manager):
        """Test max positions limit."""
        # Fill up positions
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            manager.positions[symbol] = Position(
                id=f"test_{symbol}",
                symbol=symbol,
                side=PositionSide.LONG,
                entry_price=100.0,
                quantity=10.0,
                stop_loss=95.0,
                take_profit_1=115.0,
            )

        # Should not be able to open another
        assert manager.can_open_position("TSLA") is False

    def test_can_open_position_duplicate(self, manager):
        """Test duplicate position prevention."""
        manager.positions["AAPL"] = Position(
            id="test_AAPL",
            symbol="AAPL",
            side=PositionSide.LONG,
            entry_price=100.0,
            quantity=10.0,
            stop_loss=95.0,
            take_profit_1=115.0,
        )

        # Should not be able to open duplicate
        assert manager.can_open_position("AAPL") is False

    def test_open_position(self, manager):
        """Test opening a position from signal."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )

        position = manager.open_position(signal)

        assert position is not None
        assert position.symbol == "AAPL"
        assert position.side == PositionSide.LONG
        assert position.entry_price == 150.0
        assert position.stop_loss == 145.0
        assert "AAPL" in manager.positions

    def test_close_position(self, manager):
        """Test closing a position."""
        # Open position first
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            entry_price=150.0,
            stop_loss=145.0,
            take_profit_1=165.0,
        )
        manager.open_position(signal)

        # Close position
        closed = manager.close_position("AAPL", exit_price=160.0, reason="manual")

        assert closed is not None
        assert closed.exit_price == 160.0
        assert closed.status == PositionStatus.CLOSED
        assert closed.pnl > 0
        assert "AAPL" not in manager.positions

    def test_portfolio_stats(self, manager):
        """Test portfolio statistics calculation."""
        prices = {}
        stats = manager.get_portfolio_stats(prices)

        assert "initial_capital" in stats
        assert "current_capital" in stats
        assert "portfolio_value" in stats
        assert "total_return_pct" in stats
        assert "open_positions" in stats
