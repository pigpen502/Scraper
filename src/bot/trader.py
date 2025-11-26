"""Main trading bot for Elliott Wave Trading Bot."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from ..config.settings import Settings, get_settings
from ..data.market_data import MarketDataFetcher
from ..analysis.pattern_detector import PatternDetector
from .position_manager import PositionManager
from .signals import Signal, SignalGenerator, SignalType
from ..utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class TradingBot:
    """
    Main trading bot that orchestrates Elliott Wave analysis and trading.

    Features:
    - Scans multiple symbols for Elliott Wave patterns
    - Generates trading signals based on wave position
    - Manages positions with proper risk management
    - Supports paper trading and live trading modes
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the trading bot.

        Args:
            settings: Configuration settings (uses defaults if not provided)
        """
        self.settings = settings or get_settings()

        # Set up logging
        setup_logging(
            level=self.settings.log_level,
            log_file=self.settings.log_file,
        )

        # Initialize components
        self.data_fetcher = MarketDataFetcher()
        self.signal_generator = SignalGenerator(
            min_confidence=0.6,
            min_risk_reward=2.0,
            min_wave_length=self.settings.min_wave_length,
            fib_tolerance=self.settings.fib_tolerance,
            lookback=self.settings.wave_lookback,
        )
        self.position_manager = PositionManager(
            capital=self.settings.starting_capital,
            risk_per_trade=self.settings.risk_per_trade,
            max_positions=self.settings.max_positions,
        )

        self.symbols = self.settings.symbols_list
        self.timeframe = self.settings.timeframe
        self.is_running = False
        self.last_scan_time: Optional[datetime] = None

        logger.info(f"Trading bot initialized in {self.settings.trading_mode} mode")
        logger.info(f"Watching symbols: {', '.join(self.symbols)}")

    def fetch_market_data(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch market data for all watched symbols.

        Returns:
            Dictionary of symbol -> DataFrame
        """
        logger.info(f"Fetching market data for {len(self.symbols)} symbols...")

        data = self.data_fetcher.get_multiple_symbols(
            symbols=self.symbols,
            timeframe=self.timeframe,
        )

        logger.info(f"Fetched data for {len(data)} symbols")
        return data

    def scan_for_signals(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Signal]:
        """
        Scan all symbols for trading signals.

        Args:
            data: Market data for symbols

        Returns:
            List of trading signals
        """
        logger.info("Scanning for Elliott Wave patterns...")

        signals = self.signal_generator.scan_for_signals(data)

        if signals:
            logger.info(f"Found {len(signals)} trading signals")
            for signal in signals:
                logger.info(
                    f"  {signal.symbol}: {signal.signal_type.value} "
                    f"(confidence: {signal.confidence:.2f})"
                )
        else:
            logger.info("No trading signals found")

        return signals

    def process_signals(self, signals: List[Signal]) -> List[Dict]:
        """
        Process trading signals and execute trades.

        Args:
            signals: List of trading signals

        Returns:
            List of actions taken
        """
        actions = []

        for signal in signals:
            if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                # Open new position
                position = self.position_manager.open_position(signal)
                if position:
                    actions.append({
                        "type": "open",
                        "symbol": signal.symbol,
                        "side": position.side.value,
                        "price": signal.entry_price,
                        "quantity": position.quantity,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit_1,
                    })

            elif signal.signal_type in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
                # Close existing position
                if signal.symbol in self.position_manager.positions:
                    position = self.position_manager.close_position(
                        signal.symbol,
                        signal.entry_price,
                        "wave_complete"
                    )
                    if position:
                        actions.append({
                            "type": "close",
                            "symbol": signal.symbol,
                            "price": signal.entry_price,
                            "pnl": position.pnl,
                        })

        return actions

    def update_positions(self, prices: Dict[str, float]) -> List[Dict]:
        """
        Update existing positions with current prices.

        Args:
            prices: Current prices for symbols

        Returns:
            List of actions taken (stops, TPs)
        """
        return self.position_manager.update_positions(prices)

    def get_current_prices(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Extract current prices from market data.

        Args:
            data: Market data

        Returns:
            Dictionary of symbol -> price
        """
        return {
            symbol: df["close"].iloc[-1]
            for symbol, df in data.items()
            if not df.empty
        }

    def run_once(self) -> Dict:
        """
        Run a single iteration of the trading bot.

        Returns:
            Dictionary with scan results and actions
        """
        start_time = time.time()

        # Fetch market data
        data = self.fetch_market_data()

        if not data:
            logger.warning("No market data available")
            return {"status": "no_data"}

        # Get current prices
        prices = self.get_current_prices(data)

        # Update existing positions first
        position_actions = self.update_positions(prices)

        # Scan for new signals
        signals = self.scan_for_signals(data)

        # Process signals
        signal_actions = self.process_signals(signals)

        # Get portfolio stats
        stats = self.position_manager.get_portfolio_stats(prices)

        elapsed = time.time() - start_time
        self.last_scan_time = datetime.now()

        result = {
            "status": "success",
            "timestamp": self.last_scan_time.isoformat(),
            "elapsed_seconds": elapsed,
            "symbols_scanned": len(data),
            "signals_found": len(signals),
            "position_actions": position_actions,
            "signal_actions": signal_actions,
            "portfolio": stats,
        }

        logger.info(
            f"Scan complete: {len(signals)} signals, "
            f"Portfolio: ${stats['portfolio_value']:.2f} ({stats['total_return_pct']:.2f}%)"
        )

        return result

    def run(
        self,
        interval_minutes: int = 60,
        max_iterations: Optional[int] = None,
    ) -> None:
        """
        Run the trading bot continuously.

        Args:
            interval_minutes: Minutes between scans
            max_iterations: Maximum iterations (None for infinite)
        """
        logger.info(f"Starting trading bot (interval: {interval_minutes} minutes)")
        self.is_running = True
        iteration = 0

        try:
            while self.is_running:
                if max_iterations and iteration >= max_iterations:
                    logger.info("Max iterations reached")
                    break

                iteration += 1
                logger.info(f"=== Iteration {iteration} ===")

                try:
                    result = self.run_once()
                    self._print_summary(result)
                except Exception as e:
                    logger.error(f"Error in iteration {iteration}: {e}")

                if self.is_running and (max_iterations is None or iteration < max_iterations):
                    logger.info(f"Sleeping for {interval_minutes} minutes...")
                    time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            self.is_running = False
            self._save_final_state()

    def stop(self) -> None:
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")
        self.is_running = False

    def _print_summary(self, result: Dict) -> None:
        """Print scan summary."""
        if result["status"] != "success":
            return

        portfolio = result["portfolio"]

        print("\n" + "=" * 60)
        print(f"SCAN SUMMARY - {result['timestamp']}")
        print("=" * 60)
        print(f"Symbols Scanned: {result['symbols_scanned']}")
        print(f"Signals Found: {result['signals_found']}")

        if result["signal_actions"]:
            print("\nSignal Actions:")
            for action in result["signal_actions"]:
                print(f"  - {action['type'].upper()} {action['symbol']}")

        if result["position_actions"]:
            print("\nPosition Actions:")
            for action in result["position_actions"]:
                print(f"  - {action['action']} {action['symbol']} @ ${action['price']:.2f}")

        print(f"\nPortfolio Value: ${portfolio['portfolio_value']:.2f}")
        print(f"Total Return: {portfolio['total_return_pct']:.2f}%")
        print(f"Open Positions: {portfolio['open_positions']}")
        print(f"Win Rate: {portfolio['win_rate']:.1f}%")
        print("=" * 60 + "\n")

    def _save_final_state(self) -> None:
        """Save final state when stopping."""
        logger.info("Saving final state...")
        # Position manager auto-saves on changes

    def get_status(self) -> Dict:
        """Get current bot status."""
        return {
            "is_running": self.is_running,
            "mode": self.settings.trading_mode,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "open_positions": len(self.position_manager.positions),
            "capital": self.position_manager.capital,
        }

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to watch list."""
        symbol = symbol.upper()
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            logger.info(f"Added {symbol} to watch list")

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from watch list."""
        symbol = symbol.upper()
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            logger.info(f"Removed {symbol} from watch list")

    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Perform detailed analysis on a single symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            Analysis results
        """
        logger.info(f"Analyzing {symbol}...")

        data = self.data_fetcher.get_historical_data(
            symbol=symbol,
            timeframe=self.timeframe,
        )

        if data.empty:
            return None

        signal = self.signal_generator.generate_signal(symbol, data)

        if signal is None:
            return {"symbol": symbol, "signal": None, "message": "No pattern detected"}

        return {
            "symbol": symbol,
            "signal": signal.to_dict(),
            "pattern": signal.pattern.to_dict() if signal.pattern else None,
        }
