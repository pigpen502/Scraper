#!/usr/bin/env python3
"""
Elliott Wave Trading Bot - Main Entry Point

An automated trading bot that uses Elliott Wave Theory to identify
trading opportunities in financial markets.

Usage:
    python main.py run [--interval MINUTES] [--symbols SYMBOLS]
    python main.py scan [--symbols SYMBOLS]
    python main.py analyze SYMBOL
    python main.py backtest SYMBOL [--period PERIOD]
    python main.py status
"""

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from src.config.settings import get_settings
from src.data.market_data import MarketDataFetcher
from src.bot.trader import TradingBot
from src.backtest.backtester import Backtester
from src.utils.logger import setup_logging, get_logger


def run_bot(
    symbols: Optional[List[str]] = None,
    interval: int = 60,
    max_iterations: Optional[int] = None,
) -> None:
    """Run the trading bot continuously."""
    settings = get_settings()

    bot = TradingBot(settings)

    if symbols:
        bot.symbols = [s.upper() for s in symbols]

    print("\n" + "=" * 60)
    print("ELLIOTT WAVE TRADING BOT")
    print("=" * 60)
    print(f"Mode: {settings.trading_mode}")
    print(f"Symbols: {', '.join(bot.symbols)}")
    print(f"Timeframe: {bot.timeframe}")
    print(f"Interval: {interval} minutes")
    print(f"Capital: ${settings.starting_capital:,.2f}")
    print("=" * 60 + "\n")

    try:
        bot.run(interval_minutes=interval, max_iterations=max_iterations)
    except KeyboardInterrupt:
        print("\nBot stopped by user")


def scan_markets(symbols: Optional[List[str]] = None) -> None:
    """Run a single market scan."""
    settings = get_settings()
    bot = TradingBot(settings)

    if symbols:
        bot.symbols = [s.upper() for s in symbols]

    print("\n" + "=" * 60)
    print("MARKET SCAN")
    print("=" * 60)
    print(f"Symbols: {', '.join(bot.symbols)}")
    print(f"Timeframe: {bot.timeframe}")
    print("=" * 60 + "\n")

    result = bot.run_once()

    if result["status"] == "success":
        print(f"\nScan completed at {result['timestamp']}")
        print(f"Symbols scanned: {result['symbols_scanned']}")
        print(f"Signals found: {result['signals_found']}")

        if result["signal_actions"]:
            print("\nSignal Actions:")
            for action in result["signal_actions"]:
                print(f"  {action}")
    else:
        print("Scan failed - no data available")


def analyze_symbol(symbol: str) -> None:
    """Perform detailed analysis on a single symbol."""
    settings = get_settings()
    bot = TradingBot(settings)

    print("\n" + "=" * 60)
    print(f"ANALYSIS: {symbol.upper()}")
    print("=" * 60)

    result = bot.analyze_symbol(symbol.upper())

    if result is None:
        print("Failed to fetch data for symbol")
        return

    if result["signal"] is None:
        print(f"\n{result['message']}")
        return

    signal = result["signal"]
    pattern = result.get("pattern", {})

    print(f"\nSignal Type: {signal['type'].upper()}")
    print(f"Strength: {signal['strength']}")
    print(f"Confidence: {signal['confidence']:.2f}")

    print(f"\nEntry Price: ${signal['entry']:.2f}")
    print(f"Stop Loss: ${signal['stop_loss']:.2f}")
    print(f"Take Profit 1: ${signal['take_profit_1']:.2f}")
    if signal['take_profit_2']:
        print(f"Take Profit 2: ${signal['take_profit_2']:.2f}")
    if signal['take_profit_3']:
        print(f"Take Profit 3: ${signal['take_profit_3']:.2f}")

    print(f"\nRisk/Reward Ratio: {signal['risk_reward']:.2f}")

    print(f"\nWave Position: {signal['wave_position']}")

    print("\nReasons:")
    for reason in signal.get("reasons", []):
        print(f"  - {reason}")

    if pattern:
        print(f"\nPattern Type: {pattern.get('pattern_type', 'N/A')}")
        print(f"Trend: {pattern.get('trend', 'N/A')}")


def run_backtest(
    symbol: str,
    period: str = "1y",
    initial_capital: float = 10000,
) -> None:
    """Run backtest on historical data."""
    print("\n" + "=" * 60)
    print(f"BACKTEST: {symbol.upper()}")
    print("=" * 60)
    print(f"Period: {period}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print("=" * 60)

    # Fetch historical data
    fetcher = MarketDataFetcher()
    data = fetcher.get_historical_data(
        symbol=symbol.upper(),
        timeframe="1d",
        period=period,
    )

    if data.empty:
        print("\nFailed to fetch historical data")
        return

    print(f"\nFetched {len(data)} bars of data")

    # Run backtest
    backtester = Backtester(
        initial_capital=initial_capital,
        risk_per_trade=2.0,
        min_confidence=0.6,
        min_risk_reward=2.0,
    )

    result = backtester.run(symbol.upper(), data)

    # Print results
    result.print_summary()

    # Show trade history
    if result.trades:
        print("\nTrade History (last 10):")
        print("-" * 80)
        for trade in result.trades[-10:]:
            print(
                f"  {trade.entry_time.strftime('%Y-%m-%d') if trade.entry_time else 'N/A'} | "
                f"{trade.side.upper():5} | "
                f"Entry: ${trade.entry_price:.2f} | "
                f"Exit: ${trade.exit_price:.2f} | "
                f"P&L: ${trade.pnl:+.2f} ({trade.pnl_percent:+.1f}%) | "
                f"{trade.exit_reason}"
            )


def show_status() -> None:
    """Show current bot status."""
    settings = get_settings()

    print("\n" + "=" * 60)
    print("BOT STATUS")
    print("=" * 60)
    print(f"Trading Mode: {settings.trading_mode}")
    print(f"Default Symbols: {settings.default_symbols}")
    print(f"Timeframe: {settings.timeframe}")
    print(f"Starting Capital: ${settings.starting_capital:,.2f}")
    print(f"Risk Per Trade: {settings.risk_per_trade}%")
    print(f"Max Positions: {settings.max_positions}")
    print("-" * 60)
    print(f"Min Wave Length: {settings.min_wave_length}")
    print(f"Fibonacci Tolerance: {settings.fib_tolerance}%")
    print(f"Wave Lookback: {settings.wave_lookback}")
    print("-" * 60)
    print(f"Stop Loss: {settings.stop_loss_pct}%")
    print(f"Take Profit: {settings.take_profit_pct}%")
    print(f"Trailing Stop: {settings.trailing_stop_pct}%")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Elliott Wave Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py run --interval 60 --symbols AAPL,MSFT
    python main.py scan --symbols AAPL,GOOGL,MSFT,AMZN,TSLA
    python main.py analyze AAPL
    python main.py backtest AAPL --period 2y
    python main.py status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the trading bot")
    run_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Minutes between scans (default: 60)",
    )
    run_parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to trade",
    )
    run_parser.add_argument(
        "--iterations",
        type=int,
        help="Maximum iterations (default: unlimited)",
    )

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Run a single market scan")
    scan_parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to scan",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single symbol")
    analyze_parser.add_argument("symbol", type=str, help="Symbol to analyze")

    # Backtest command
    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument("symbol", type=str, help="Symbol to backtest")
    backtest_parser.add_argument(
        "--period",
        type=str,
        default="1y",
        help="Historical period (e.g., 6mo, 1y, 2y)",
    )
    backtest_parser.add_argument(
        "--capital",
        type=float,
        default=10000,
        help="Initial capital for backtest",
    )

    # Status command
    subparsers.add_parser("status", help="Show bot status")

    args = parser.parse_args()

    # Set up logging
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    if args.command == "run":
        symbols = args.symbols.split(",") if args.symbols else None
        run_bot(symbols=symbols, interval=args.interval, max_iterations=args.iterations)

    elif args.command == "scan":
        symbols = args.symbols.split(",") if args.symbols else None
        scan_markets(symbols=symbols)

    elif args.command == "analyze":
        analyze_symbol(args.symbol)

    elif args.command == "backtest":
        run_backtest(args.symbol, period=args.period, initial_capital=args.capital)

    elif args.command == "status":
        show_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
