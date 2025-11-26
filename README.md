# Elliott Wave Trading Bot

An automated trading bot that uses Elliott Wave Theory to identify trading opportunities in financial markets. Available as both a **Python bot** and **TradingView Pine Script** indicators.

## Two Versions Available

### 1. Python Bot (`src/`)
Full-featured automated trading bot with backtesting, paper trading, and live trading support.

### 2. TradingView Scripts (`tradingview/`)
Pine Script indicators and strategies for TradingView charts with visual wave detection and alerts.

---

## Features

- **Elliott Wave Pattern Detection**: Identifies 5-wave impulse patterns and 3-wave corrective patterns
- **Fibonacci Analysis**: Uses Fibonacci retracements and extensions for wave validation and price targets
- **Technical Confirmation**: Combines wave analysis with RSI, MACD, Bollinger Bands, and other indicators
- **Risk Management**: Automatic position sizing based on risk percentage
- **Backtesting**: Test strategies on historical data before live trading
- **Paper Trading**: Simulate trades without risking real capital

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd Scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your settings
```

## Quick Start

### 1. Analyze a Symbol

```bash
python main.py analyze AAPL
```

This performs detailed Elliott Wave analysis on a single symbol and shows:
- Current wave position
- Trading signal (buy/sell/hold)
- Entry, stop loss, and take profit levels
- Supporting technical indicators

### 2. Scan Multiple Symbols

```bash
python main.py scan --symbols AAPL,MSFT,GOOGL,AMZN,TSLA
```

Scans multiple symbols for trading opportunities.

### 3. Run Backtest

```bash
python main.py backtest AAPL --period 2y --capital 10000
```

Tests the strategy on historical data and shows:
- Total return
- Win rate
- Maximum drawdown
- Sharpe ratio
- Trade history

### 4. Run the Bot

```bash
# Paper trading mode
python main.py run --interval 60 --symbols AAPL,MSFT,GOOGL

# With limited iterations (for testing)
python main.py run --interval 5 --iterations 3
```

## Configuration

Edit `.env` file to customize settings:

```env
# Trading Mode
TRADING_MODE=paper  # 'paper' or 'live'

# Capital & Risk
STARTING_CAPITAL=10000
RISK_PER_TRADE=2.0
MAX_POSITIONS=5

# Symbols
DEFAULT_SYMBOLS=AAPL,MSFT,GOOGL,AMZN,TSLA

# Timeframe
TIMEFRAME=1h  # 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk

# Elliott Wave Settings
MIN_WAVE_LENGTH=5
FIB_TOLERANCE=10.0
WAVE_LOOKBACK=100

# Risk Management
STOP_LOSS_PCT=2.0
TAKE_PROFIT_PCT=6.0
TRAILING_STOP_PCT=3.0
```

## Elliott Wave Theory Overview

### Impulse Waves (5-wave pattern)
- **Wave 1**: Initial move in trend direction
- **Wave 2**: Retracement (typically 50-61.8% of Wave 1)
- **Wave 3**: Strongest wave, never the shortest
- **Wave 4**: Consolidation (typically 38.2-50% of Wave 3)
- **Wave 5**: Final move, often equals Wave 1

### Corrective Waves (3-wave pattern)
- **Wave A**: Initial counter-trend move
- **Wave B**: Partial retracement of Wave A
- **Wave C**: Final counter-trend move, often equals Wave A

### Key Rules
1. Wave 2 never retraces more than 100% of Wave 1
2. Wave 3 is never the shortest among waves 1, 3, and 5
3. Wave 4 never enters the price territory of Wave 1

## Project Structure

```
Scraper/
├── src/
│   ├── analysis/           # Elliott Wave & technical analysis
│   │   ├── elliott_wave.py # Core wave detection
│   │   ├── indicators.py   # Technical indicators
│   │   └── pattern_detector.py
│   ├── bot/                # Trading bot logic
│   │   ├── signals.py      # Signal generation
│   │   ├── position_manager.py
│   │   └── trader.py       # Main bot
│   ├── config/             # Configuration
│   │   └── settings.py
│   ├── data/               # Data fetching
│   │   └── market_data.py
│   ├── backtest/           # Backtesting
│   │   └── backtester.py
│   └── utils/              # Utilities
│       ├── logger.py
│       └── helpers.py
├── tests/                  # Test files
├── logs/                   # Log files
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
└── .env.example           # Environment template
```

## Trading Signals

The bot generates signals based on wave position:

| Wave Position | Signal | Rationale |
|--------------|--------|-----------|
| End of Wave 2 | BUY | Wave 3 starting (strongest wave) |
| End of Wave 4 | BUY | Wave 5 starting |
| End of Wave 5 | CLOSE | Impulse complete, expect correction |
| End of ABC | BUY/SELL | Correction complete, new impulse starting |

## Risk Management

- **Position Sizing**: Based on risk percentage and stop loss distance
- **Stop Loss**: Set at wave invalidation level
- **Take Profit**: Multiple targets based on Fibonacci extensions
- **Trailing Stop**: Activated after price moves in favor

---

## TradingView Version

The `tradingview/` folder contains Pine Script indicators for TradingView:

### Included Scripts

| Script | Description |
|--------|-------------|
| `elliott_wave_indicator.pine` | Main wave detection with visual labels |
| `elliott_wave_strategy.pine` | Backtestable trading strategy |
| `elliott_wave_oscillator.pine` | Wave momentum oscillator (5/35 EMA) |
| `fibonacci_auto_levels.pine` | Auto Fibonacci retracement/extension |
| `elliott_wave_alerts.pine` | Comprehensive alert system |

### TradingView Installation

1. Open TradingView and go to **Pine Editor**
2. Copy contents of any `.pine` file
3. Paste into Pine Editor
4. Click **"Add to Chart"**

### Recommended Setup

Add these indicators to your chart:

1. **Elliott Wave Auto-Detection** (overlay)
2. **Auto Fibonacci Levels** (overlay)
3. **Elliott Wave Oscillator** (separate pane)

Or use the **Elliott Wave Strategy** for automated backtesting.

### Setting Up Alerts

1. Add indicator to chart
2. Right-click → "Add Alert"
3. Select Elliott Wave indicator
4. Choose alert condition (Buy/Sell/Divergence)
5. Configure notifications

See `tradingview/README.md` for detailed documentation.

---

## Disclaimer

This software is for educational purposes only. Trading financial instruments involves substantial risk of loss. Past performance does not guarantee future results. Always do your own research and never trade with money you cannot afford to lose.

## License

MIT License
