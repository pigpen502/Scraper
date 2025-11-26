"""Backtesting engine for Elliott Wave Trading Bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from ..analysis.pattern_detector import PatternDetector
from ..analysis.indicators import TechnicalIndicators
from ..bot.signals import SignalGenerator, Signal, SignalType
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    """Represents a completed trade in backtest."""

    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    quantity: float
    pnl: float
    pnl_percent: float
    exit_reason: str  # 'stop_loss', 'take_profit', 'signal'
    bars_held: int


@dataclass
class BacktestResult:
    """Results of a backtest run."""

    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    largest_winner: float = 0.0
    largest_loser: float = 0.0
    avg_bars_held: float = 0.0
    total_bars: int = 0
    signals_generated: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "total_trades": len(self.trades),
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_trade_pnl": self.avg_trade_pnl,
            "avg_winner": self.avg_winner,
            "avg_loser": self.avg_loser,
            "largest_winner": self.largest_winner,
            "largest_loser": self.largest_loser,
            "avg_bars_held": self.avg_bars_held,
            "signals_generated": self.signals_generated,
        }

    def print_summary(self) -> None:
        """Print backtest summary."""
        print("\n" + "=" * 60)
        print(f"BACKTEST RESULTS - {self.symbol}")
        print("=" * 60)
        print(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        print(f"Total Bars: {self.total_bars}")
        print("-" * 60)
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${self.final_capital:,.2f}")
        print(f"Total Return: ${self.total_return:,.2f} ({self.total_return_pct:.2f}%)")
        print("-" * 60)
        print(f"Total Trades: {len(self.trades)}")
        print(f"Signals Generated: {self.signals_generated}")
        print(f"Win Rate: {self.win_rate:.2f}%")
        print(f"Profit Factor: {self.profit_factor:.2f}")
        print("-" * 60)
        print(f"Max Drawdown: ${self.max_drawdown:,.2f} ({self.max_drawdown_pct:.2f}%)")
        print(f"Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print("-" * 60)
        print(f"Avg Trade P&L: ${self.avg_trade_pnl:.2f}")
        print(f"Avg Winner: ${self.avg_winner:.2f}")
        print(f"Avg Loser: ${self.avg_loser:.2f}")
        print(f"Largest Winner: ${self.largest_winner:.2f}")
        print(f"Largest Loser: ${self.largest_loser:.2f}")
        print(f"Avg Bars Held: {self.avg_bars_held:.1f}")
        print("=" * 60 + "\n")


class Backtester:
    """
    Backtesting engine for Elliott Wave trading strategies.

    Simulates trading on historical data to evaluate strategy performance.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 2.0,
        min_confidence: float = 0.6,
        min_risk_reward: float = 2.0,
        commission: float = 0.0,
        slippage: float = 0.0,
    ):
        """
        Initialize the backtester.

        Args:
            initial_capital: Starting capital
            risk_per_trade: Risk per trade (percentage)
            min_confidence: Minimum signal confidence
            min_risk_reward: Minimum risk/reward ratio
            commission: Commission per trade (percentage)
            slippage: Slippage per trade (percentage)
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.commission = commission
        self.slippage = slippage

        self.signal_generator = SignalGenerator(
            min_confidence=min_confidence,
            min_risk_reward=min_risk_reward,
        )

    def run(
        self,
        symbol: str,
        data: pd.DataFrame,
        lookback: int = 100,
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            lookback: Number of bars for pattern detection

        Returns:
            BacktestResult object
        """
        if len(data) < lookback + 50:
            logger.warning(f"Insufficient data for backtesting {symbol}")
            return self._empty_result(symbol)

        logger.info(f"Running backtest for {symbol} ({len(data)} bars)")

        capital = self.initial_capital
        equity_curve = [capital]
        trades: List[Trade] = []
        signals_count = 0

        # Current position state
        in_position = False
        position_side = None
        entry_price = 0.0
        entry_time = None
        entry_bar = 0
        stop_loss = 0.0
        take_profit_1 = 0.0
        take_profit_2 = None
        quantity = 0.0

        # Iterate through data
        for i in range(lookback, len(data)):
            current_bar = data.iloc[i]
            current_price = current_bar["close"]
            current_high = current_bar["high"]
            current_low = current_bar["low"]
            current_time = data.index[i] if isinstance(data.index[i], datetime) else datetime.now()

            # Check if we need to exit current position
            if in_position:
                exit_price = None
                exit_reason = None

                # Check stop loss
                if position_side == "long" and current_low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "stop_loss"
                elif position_side == "short" and current_high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "stop_loss"

                # Check take profit
                if exit_price is None:
                    if position_side == "long" and current_high >= take_profit_1:
                        exit_price = take_profit_1
                        exit_reason = "take_profit"
                    elif position_side == "short" and current_low <= take_profit_1:
                        exit_price = take_profit_1
                        exit_reason = "take_profit"

                # Execute exit if triggered
                if exit_price is not None:
                    # Apply slippage
                    if position_side == "long":
                        exit_price *= (1 - self.slippage / 100)
                    else:
                        exit_price *= (1 + self.slippage / 100)

                    # Calculate P&L
                    if position_side == "long":
                        pnl = (exit_price - entry_price) * quantity
                    else:
                        pnl = (entry_price - exit_price) * quantity

                    # Apply commission
                    pnl -= (entry_price + exit_price) * quantity * (self.commission / 100)

                    pnl_pct = (pnl / (entry_price * quantity)) * 100

                    # Record trade
                    trade = Trade(
                        symbol=symbol,
                        side=position_side,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        entry_time=entry_time,
                        exit_time=current_time,
                        quantity=quantity,
                        pnl=pnl,
                        pnl_percent=pnl_pct,
                        exit_reason=exit_reason,
                        bars_held=i - entry_bar,
                    )
                    trades.append(trade)

                    # Update capital
                    capital += pnl

                    # Reset position
                    in_position = False
                    position_side = None

            # Look for new signals if not in position
            if not in_position:
                # Get data window for analysis
                window = data.iloc[i - lookback : i + 1].copy()

                # Generate signal
                signal = self.signal_generator.generate_signal(symbol, window)

                if signal:
                    signals_count += 1

                    # Only trade BUY and SELL signals
                    if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                        # Calculate position size
                        risk_amount = capital * (self.risk_per_trade / 100)
                        risk_per_share = abs(current_price - signal.stop_loss)

                        if risk_per_share > 0:
                            quantity = risk_amount / risk_per_share

                            # Apply slippage to entry
                            if signal.signal_type == SignalType.BUY:
                                entry_price = current_price * (1 + self.slippage / 100)
                                position_side = "long"
                            else:
                                entry_price = current_price * (1 - self.slippage / 100)
                                position_side = "short"

                            in_position = True
                            entry_time = current_time
                            entry_bar = i
                            stop_loss = signal.stop_loss
                            take_profit_1 = signal.take_profit_1
                            take_profit_2 = signal.take_profit_2

            # Update equity curve
            if in_position:
                if position_side == "long":
                    unrealized = (current_price - entry_price) * quantity
                else:
                    unrealized = (entry_price - current_price) * quantity
                equity_curve.append(capital + unrealized)
            else:
                equity_curve.append(capital)

        # Close any remaining position at last price
        if in_position:
            final_price = data["close"].iloc[-1]
            if position_side == "long":
                pnl = (final_price - entry_price) * quantity
            else:
                pnl = (entry_price - final_price) * quantity

            capital += pnl

            trade = Trade(
                symbol=symbol,
                side=position_side,
                entry_price=entry_price,
                exit_price=final_price,
                entry_time=entry_time,
                exit_time=data.index[-1] if isinstance(data.index[-1], datetime) else datetime.now(),
                quantity=quantity,
                pnl=pnl,
                pnl_percent=(pnl / (entry_price * quantity)) * 100,
                exit_reason="end_of_data",
                bars_held=len(data) - entry_bar,
            )
            trades.append(trade)

        # Calculate statistics
        result = self._calculate_statistics(
            symbol=symbol,
            data=data,
            trades=trades,
            equity_curve=equity_curve,
            final_capital=capital,
            signals_count=signals_count,
        )

        return result

    def _calculate_statistics(
        self,
        symbol: str,
        data: pd.DataFrame,
        trades: List[Trade],
        equity_curve: List[float],
        final_capital: float,
        signals_count: int,
    ) -> BacktestResult:
        """Calculate backtest statistics."""
        # Convert index to datetime if possible
        try:
            start_date = pd.to_datetime(data.index[0])
            end_date = pd.to_datetime(data.index[-1])
        except:
            start_date = datetime.now()
            end_date = datetime.now()

        result = BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=final_capital - self.initial_capital,
            total_return_pct=((final_capital - self.initial_capital) / self.initial_capital) * 100,
            trades=trades,
            equity_curve=equity_curve,
            total_bars=len(data),
            signals_generated=signals_count,
        )

        if not trades:
            return result

        # Win/loss analysis
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]

        result.win_rate = (len(winners) / len(trades)) * 100 if trades else 0

        # Average trade stats
        result.avg_trade_pnl = sum(t.pnl for t in trades) / len(trades)
        result.avg_winner = sum(t.pnl for t in winners) / len(winners) if winners else 0
        result.avg_loser = sum(t.pnl for t in losers) / len(losers) if losers else 0

        # Largest win/loss
        result.largest_winner = max((t.pnl for t in trades), default=0)
        result.largest_loser = min((t.pnl for t in trades), default=0)

        # Average bars held
        result.avg_bars_held = sum(t.bars_held for t in trades) / len(trades)

        # Profit factor
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Max drawdown
        equity_array = np.array(equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = peak - equity_array
        result.max_drawdown = drawdown.max()
        result.max_drawdown_pct = (result.max_drawdown / peak[np.argmax(drawdown)]) * 100 if peak.max() > 0 else 0

        # Sharpe ratio (simplified - daily returns)
        returns = np.diff(equity_array) / equity_array[:-1]
        if len(returns) > 1 and returns.std() > 0:
            result.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
        else:
            result.sharpe_ratio = 0

        return result

    def _empty_result(self, symbol: str) -> BacktestResult:
        """Create empty result for insufficient data."""
        return BacktestResult(
            symbol=symbol,
            start_date=datetime.now(),
            end_date=datetime.now(),
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0,
            total_return_pct=0,
        )

    def run_multiple(
        self,
        data: Dict[str, pd.DataFrame],
        lookback: int = 100,
    ) -> Dict[str, BacktestResult]:
        """
        Run backtest on multiple symbols.

        Args:
            data: Dictionary of symbol -> DataFrame
            lookback: Lookback period

        Returns:
            Dictionary of symbol -> BacktestResult
        """
        results = {}

        for symbol, df in data.items():
            logger.info(f"Backtesting {symbol}...")
            results[symbol] = self.run(symbol, df, lookback)

        return results

    def optimize(
        self,
        symbol: str,
        data: pd.DataFrame,
        param_grid: Dict,
    ) -> List[Tuple[Dict, BacktestResult]]:
        """
        Optimize strategy parameters.

        Args:
            symbol: Trading symbol
            data: Historical data
            param_grid: Parameter grid for optimization

        Returns:
            List of (params, result) tuples sorted by return
        """
        from itertools import product

        # Generate all parameter combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = list(product(*values))

        results = []

        for combo in combinations:
            params = dict(zip(keys, combo))
            logger.info(f"Testing params: {params}")

            # Update backtester settings
            self.min_confidence = params.get("min_confidence", self.min_confidence)
            self.risk_per_trade = params.get("risk_per_trade", self.risk_per_trade)
            self.min_risk_reward = params.get("min_risk_reward", self.min_risk_reward)

            # Recreate signal generator with new params
            self.signal_generator = SignalGenerator(
                min_confidence=self.min_confidence,
                min_risk_reward=self.min_risk_reward,
            )

            # Run backtest
            result = self.run(symbol, data)
            results.append((params, result))

        # Sort by total return
        results.sort(key=lambda x: x[1].total_return_pct, reverse=True)

        return results
