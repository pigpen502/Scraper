"""Position management for Elliott Wave Trading Bot."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .signals import Signal, SignalType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PositionStatus(Enum):
    """Position status."""

    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"
    TARGET_HIT = "target_hit"


class PositionSide(Enum):
    """Position side."""

    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """Represents a trading position."""

    id: str
    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    entry_time: datetime = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: PositionStatus = PositionStatus.OPEN
    pnl: float = 0.0
    pnl_percent: float = 0.0
    trailing_stop: Optional[float] = None
    partial_exits: List[Dict] = field(default_factory=list)
    signal: Optional[Signal] = None

    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()

    @property
    def current_value(self) -> float:
        """Calculate current position value."""
        return self.entry_price * self.quantity

    @property
    def remaining_quantity(self) -> float:
        """Get remaining quantity after partial exits."""
        exited = sum(p.get("quantity", 0) for p in self.partial_exits)
        return self.quantity - exited

    def calculate_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized P&L.

        Args:
            current_price: Current market price

        Returns:
            P&L amount
        """
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.remaining_quantity
        else:
            return (self.entry_price - current_price) * self.remaining_quantity

    def calculate_pnl_percent(self, current_price: float) -> float:
        """Calculate P&L percentage."""
        if self.entry_price == 0:
            return 0.0

        if self.side == PositionSide.LONG:
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - current_price) / self.entry_price) * 100

    def should_stop_out(self, current_price: float) -> bool:
        """Check if position should be stopped out."""
        stop = self.trailing_stop or self.stop_loss

        if self.side == PositionSide.LONG:
            return current_price <= stop
        else:
            return current_price >= stop

    def should_take_profit(self, current_price: float) -> int:
        """
        Check which take profit level is hit.

        Returns:
            0 if none, 1/2/3 for TP level hit
        """
        if self.side == PositionSide.LONG:
            if self.take_profit_3 and current_price >= self.take_profit_3:
                return 3
            if self.take_profit_2 and current_price >= self.take_profit_2:
                return 2
            if current_price >= self.take_profit_1:
                return 1
        else:
            if self.take_profit_3 and current_price <= self.take_profit_3:
                return 3
            if self.take_profit_2 and current_price <= self.take_profit_2:
                return 2
            if current_price <= self.take_profit_1:
                return 1

        return 0

    def update_trailing_stop(
        self, current_price: float, trailing_pct: float = 3.0
    ) -> bool:
        """
        Update trailing stop if price moved favorably.

        Args:
            current_price: Current market price
            trailing_pct: Trailing stop percentage

        Returns:
            True if trailing stop was updated
        """
        trailing_distance = current_price * (trailing_pct / 100)

        if self.side == PositionSide.LONG:
            new_stop = current_price - trailing_distance
            if self.trailing_stop is None or new_stop > self.trailing_stop:
                if new_stop > self.stop_loss:  # Only trail if above original stop
                    self.trailing_stop = new_stop
                    return True
        else:
            new_stop = current_price + trailing_distance
            if self.trailing_stop is None or new_stop < self.trailing_stop:
                if new_stop < self.stop_loss:
                    self.trailing_stop = new_stop
                    return True

        return False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "status": self.status.value,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "trailing_stop": self.trailing_stop,
            "partial_exits": self.partial_exits,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            symbol=data["symbol"],
            side=PositionSide(data["side"]),
            entry_price=data["entry_price"],
            quantity=data["quantity"],
            stop_loss=data["stop_loss"],
            take_profit_1=data["take_profit_1"],
            take_profit_2=data.get("take_profit_2"),
            take_profit_3=data.get("take_profit_3"),
            entry_time=datetime.fromisoformat(data["entry_time"]) if data.get("entry_time") else None,
            exit_price=data.get("exit_price"),
            exit_time=datetime.fromisoformat(data["exit_time"]) if data.get("exit_time") else None,
            status=PositionStatus(data.get("status", "open")),
            pnl=data.get("pnl", 0.0),
            pnl_percent=data.get("pnl_percent", 0.0),
            trailing_stop=data.get("trailing_stop"),
            partial_exits=data.get("partial_exits", []),
        )


class PositionManager:
    """
    Manages trading positions with risk management.
    """

    def __init__(
        self,
        capital: float,
        risk_per_trade: float = 2.0,
        max_positions: int = 5,
        state_file: str = "portfolio_state.json",
    ):
        """
        Initialize position manager.

        Args:
            capital: Starting capital
            risk_per_trade: Maximum risk per trade (percentage)
            max_positions: Maximum concurrent positions
            state_file: File to persist state
        """
        self.initial_capital = capital
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        self.state_file = Path(state_file)

        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.position_counter = 0

        # Load existing state if available
        self._load_state()

    def calculate_position_size(
        self, entry_price: float, stop_loss: float
    ) -> float:
        """
        Calculate position size based on risk management.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price

        Returns:
            Number of shares/units to trade
        """
        risk_amount = self.capital * (self.risk_per_trade / 100)
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return 0

        position_size = risk_amount / risk_per_share

        # Ensure position value doesn't exceed available capital
        max_position_value = self.capital * 0.25  # Max 25% of capital per position
        max_shares = max_position_value / entry_price

        return min(position_size, max_shares)

    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position."""
        # Check max positions
        if len(self.positions) >= self.max_positions:
            logger.warning(f"Max positions reached ({self.max_positions})")
            return False

        # Check if already have position in symbol
        if symbol in self.positions:
            logger.warning(f"Already have position in {symbol}")
            return False

        return True

    def open_position(self, signal: Signal) -> Optional[Position]:
        """
        Open a new position from a signal.

        Args:
            signal: Trading signal

        Returns:
            Position object or None
        """
        if not self.can_open_position(signal.symbol):
            return None

        # Calculate position size
        quantity = self.calculate_position_size(
            signal.entry_price, signal.stop_loss
        )

        if quantity <= 0:
            logger.warning(f"Invalid position size for {signal.symbol}")
            return None

        # Determine side
        if signal.signal_type in [SignalType.BUY]:
            side = PositionSide.LONG
        elif signal.signal_type in [SignalType.SELL]:
            side = PositionSide.SHORT
        else:
            return None

        self.position_counter += 1
        position_id = f"pos_{self.position_counter}_{signal.symbol}"

        position = Position(
            id=position_id,
            symbol=signal.symbol,
            side=side,
            entry_price=signal.entry_price,
            quantity=quantity,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
            take_profit_3=signal.take_profit_3,
            signal=signal,
        )

        self.positions[signal.symbol] = position
        self._save_state()

        logger.info(
            f"Opened {side.value} position for {signal.symbol}: "
            f"{quantity:.2f} shares @ ${signal.entry_price:.2f}"
        )

        return position

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "manual",
    ) -> Optional[Position]:
        """
        Close a position.

        Args:
            symbol: Symbol to close
            exit_price: Exit price
            reason: Reason for closing

        Returns:
            Closed position
        """
        if symbol not in self.positions:
            return None

        position = self.positions.pop(symbol)
        position.exit_price = exit_price
        position.exit_time = datetime.now()

        # Calculate P&L
        position.pnl = position.calculate_pnl(exit_price)
        position.pnl_percent = position.calculate_pnl_percent(exit_price)

        # Update status based on reason
        if reason == "stop_loss":
            position.status = PositionStatus.STOPPED
        elif reason == "take_profit":
            position.status = PositionStatus.TARGET_HIT
        else:
            position.status = PositionStatus.CLOSED

        # Update capital
        self.capital += position.pnl

        self.closed_positions.append(position)
        self._save_state()

        logger.info(
            f"Closed {symbol} position: P&L ${position.pnl:.2f} ({position.pnl_percent:.2f}%) - {reason}"
        )

        return position

    def partial_close(
        self,
        symbol: str,
        exit_price: float,
        quantity_pct: float = 50.0,
    ) -> Optional[Dict]:
        """
        Partially close a position.

        Args:
            symbol: Symbol
            exit_price: Exit price
            quantity_pct: Percentage of position to close

        Returns:
            Partial exit details
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        exit_quantity = position.remaining_quantity * (quantity_pct / 100)

        # Calculate P&L for partial exit
        if position.side == PositionSide.LONG:
            pnl = (exit_price - position.entry_price) * exit_quantity
        else:
            pnl = (position.entry_price - exit_price) * exit_quantity

        partial_exit = {
            "quantity": exit_quantity,
            "price": exit_price,
            "pnl": pnl,
            "time": datetime.now().isoformat(),
        }

        position.partial_exits.append(partial_exit)
        self.capital += pnl
        self._save_state()

        logger.info(
            f"Partial close {symbol}: {exit_quantity:.2f} @ ${exit_price:.2f}, P&L ${pnl:.2f}"
        )

        return partial_exit

    def update_positions(self, prices: Dict[str, float]) -> List[Dict]:
        """
        Update all positions with current prices.

        Args:
            prices: Dictionary of symbol -> current price

        Returns:
            List of actions taken
        """
        actions = []

        for symbol, position in list(self.positions.items()):
            if symbol not in prices:
                continue

            current_price = prices[symbol]

            # Check stop loss
            if position.should_stop_out(current_price):
                self.close_position(symbol, current_price, "stop_loss")
                actions.append({
                    "symbol": symbol,
                    "action": "stop_loss",
                    "price": current_price,
                })
                continue

            # Check take profit levels
            tp_level = position.should_take_profit(current_price)
            if tp_level > 0:
                if tp_level == 3:
                    # Close entire position
                    self.close_position(symbol, current_price, "take_profit")
                    actions.append({
                        "symbol": symbol,
                        "action": f"take_profit_{tp_level}",
                        "price": current_price,
                    })
                else:
                    # Partial close
                    pct = 33 if tp_level == 1 else 50
                    self.partial_close(symbol, current_price, pct)
                    actions.append({
                        "symbol": symbol,
                        "action": f"partial_close_tp{tp_level}",
                        "price": current_price,
                    })

            # Update trailing stop
            position.update_trailing_stop(current_price)

        return actions

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value."""
        value = self.capital

        for symbol, position in self.positions.items():
            if symbol in prices:
                value += position.calculate_pnl(prices[symbol])

        return value

    def get_portfolio_stats(self, prices: Dict[str, float]) -> Dict:
        """Get portfolio statistics."""
        total_pnl = sum(p.pnl for p in self.closed_positions)
        unrealized_pnl = sum(
            p.calculate_pnl(prices.get(p.symbol, p.entry_price))
            for p in self.positions.values()
        )

        winning_trades = [p for p in self.closed_positions if p.pnl > 0]
        losing_trades = [p for p in self.closed_positions if p.pnl <= 0]

        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.capital,
            "portfolio_value": self.get_portfolio_value(prices),
            "total_return_pct": ((self.get_portfolio_value(prices) - self.initial_capital) / self.initial_capital) * 100,
            "realized_pnl": total_pnl,
            "unrealized_pnl": unrealized_pnl,
            "open_positions": len(self.positions),
            "total_trades": len(self.closed_positions),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.closed_positions) * 100 if self.closed_positions else 0,
            "avg_win": sum(p.pnl for p in winning_trades) / len(winning_trades) if winning_trades else 0,
            "avg_loss": sum(p.pnl for p in losing_trades) / len(losing_trades) if losing_trades else 0,
        }

    def _save_state(self) -> None:
        """Save state to file."""
        state = {
            "capital": self.capital,
            "position_counter": self.position_counter,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "closed_positions": [p.to_dict() for p in self.closed_positions[-100:]],  # Keep last 100
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            self.capital = state.get("capital", self.capital)
            self.position_counter = state.get("position_counter", 0)

            self.positions = {
                s: Position.from_dict(p)
                for s, p in state.get("positions", {}).items()
            }

            self.closed_positions = [
                Position.from_dict(p)
                for p in state.get("closed_positions", [])
            ]

            logger.info(f"Loaded state: {len(self.positions)} open positions")

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
