# Elliott Wave Trading Bot - TradingView Edition

A comprehensive suite of TradingView Pine Script indicators and strategies for automated Elliott Wave analysis and trading.

## Indicators Included

### 1. Elliott Wave Auto-Detection (`elliott_wave_indicator.pine`)

The main indicator that automatically detects and visualizes Elliott Wave patterns on your charts.

**Features:**
- Automatic pivot point detection
- 5-wave impulse pattern recognition
- Wave validation using Elliott Wave rules
- Fibonacci relationship validation
- Visual wave labeling (0-5)
- Price target projections
- Invalidation level display
- Buy/Sell signals at wave completion

**Key Settings:**
- `Pivot Detection Length`: Sensitivity for swing detection (default: 5)
- `Minimum Wave Length`: Minimum bars per wave (default: 5)
- `Fibonacci Tolerance`: Allowance for Fib ratios (default: 15%)

### 2. Elliott Wave Strategy (`elliott_wave_strategy.pine`)

A complete backtestable trading strategy based on Elliott Wave Theory.

**Features:**
- Automated entry at Wave 2 and Wave 4 completion
- Exit at Wave 5 completion
- Risk-based position sizing
- Multiple take profit levels (TP1, TP2, TP3)
- Trailing stop loss
- Technical confirmation filters (RSI, MACD, EMA)
- Full backtest statistics

**Entry Conditions:**
- Wave 2 or Wave 4 complete in detected pattern
- Minimum confidence threshold met
- All technical filters aligned
- Minimum risk/reward ratio achieved

**Risk Management:**
- Position sizing based on risk percentage
- Stop loss at wave invalidation level
- Partial profit taking at TP1
- Trailing stop for remaining position

### 3. Elliott Wave Oscillator (`elliott_wave_oscillator.pine`)

A momentum oscillator specifically designed for Elliott Wave analysis.

**Features:**
- 5/35 EMA difference (classic EWO)
- Signal line for crossover detection
- Histogram for momentum visualization
- Divergence detection (bullish/bearish)
- Wave 3 identification (strongest momentum)
- Zero line cross signals

**How to Use:**
- **Wave 3**: Look for the highest oscillator reading
- **Wave 5 Divergence**: Price makes new high, oscillator doesn't
- **Zero Crosses**: Indicate wave transitions

### 4. Auto Fibonacci Levels (`fibonacci_auto_levels.pine`)

Automatically draws Fibonacci retracement and extension levels.

**Features:**
- Automatic swing high/low detection
- Retracement levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
- Extension levels: 100%, 127.2%, 161.8%, 200%, 261.8%
- Price proximity alerts
- Dynamic level updates
- Customizable colors and display

**Wave-Specific Targets:**
- **Wave 2**: 38.2%, 50%, or 61.8% retracement of Wave 1
- **Wave 3**: 161.8%, 200%, or 261.8% extension
- **Wave 4**: 38.2% or 50% retracement of Wave 3
- **Wave 5**: Equal to Wave 1, or 61.8% of Waves 1-3

### 5. Elliott Wave Alert System (`elliott_wave_alerts.pine`)

A comprehensive alert system combining wave detection with technical analysis.

**Features:**
- Multi-factor confidence scoring
- RSI, MACD, EMA confluence analysis
- Divergence detection
- Customizable alert thresholds
- High-confidence signal highlighting
- Real-time status dashboard

**Confidence Score Components:**
- Wave pattern validity (up to 50%)
- RSI position (up to 15%)
- MACD alignment (up to 10%)
- EMA structure (up to 15%)
- EWO direction (up to 10%)

## Installation

### Method 1: Copy & Paste

1. Open TradingView and go to **Pine Editor** (bottom panel)
2. Delete any existing code
3. Copy the entire contents of the `.pine` file you want to use
4. Paste into the Pine Editor
5. Click **"Add to Chart"** or press `Ctrl+Enter`
6. Adjust settings in the indicator panel

### Method 2: Import from File

1. In TradingView, click on **Pine Editor**
2. Click **"Open"** → **"Import from file"**
3. Select the `.pine` file
4. Click **"Add to Chart"**

## Recommended Setup

For comprehensive Elliott Wave analysis, add indicators in this order:

1. **Elliott Wave Auto-Detection** (main chart overlay)
2. **Auto Fibonacci Levels** (main chart overlay)
3. **Elliott Wave Oscillator** (separate pane below)
4. **Elliott Wave Alert System** (for alerts only)

Or use the **Elliott Wave Strategy** for backtesting and automated trading.

## Setting Up Alerts

### In TradingView:

1. Add the indicator to your chart
2. Right-click on the chart → **"Add Alert"**
3. In the **Condition** dropdown, select the Elliott Wave indicator
4. Choose the specific alert condition:
   - `Buy Signal` - Wave 2/4 complete (bullish)
   - `Sell Signal` - Wave 2/4 complete (bearish)
   - `High Confidence Buy/Sell` - 80%+ confidence
   - `Bullish/Bearish Divergence` - Wave 5 ending signals
5. Set your notification preferences (popup, email, webhook, etc.)
6. Click **"Create"**

### Webhook Integration:

For automated trading, use TradingView's webhook feature:

```
Alert Message Template:
{
  "symbol": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "time": "{{time}}"
}
```

## Trading Rules

### Entry Signals

| Wave Position | Signal | Action |
|--------------|--------|--------|
| Wave 2 Complete (Bullish) | BUY | Enter long, stop below Wave 2 low |
| Wave 4 Complete (Bullish) | BUY | Enter long, stop below Wave 4 low |
| Wave 2 Complete (Bearish) | SELL | Enter short, stop above Wave 2 high |
| Wave 4 Complete (Bearish) | SELL | Enter short, stop above Wave 4 high |

### Exit Signals

| Condition | Action |
|-----------|--------|
| Wave 5 Complete | Close position |
| Divergence Detected | Tighten stops / partial exit |
| Stop Loss Hit | Exit immediately |
| TP1 Hit | Close 50% position |
| TP2 Hit | Close 30% position |
| TP3 Hit | Close remaining |

### Invalidation Rules

- **Bullish Wave**: If price drops below Wave 1 end during Wave 4, pattern invalid
- **Bearish Wave**: If price rises above Wave 1 end during Wave 4, pattern invalid
- Always use invalidation level as maximum stop loss

## Elliott Wave Rules Summary

### Three Cardinal Rules (Never Violated)

1. **Wave 2** never retraces more than 100% of Wave 1
2. **Wave 3** is never the shortest of waves 1, 3, and 5
3. **Wave 4** never enters the price territory of Wave 1

### Common Fibonacci Relationships

| Wave | Typical Fibonacci Levels |
|------|-------------------------|
| Wave 2 | 50%, 61.8%, 78.6% retracement of Wave 1 |
| Wave 3 | 161.8%, 200%, 261.8% of Wave 1 |
| Wave 4 | 38.2%, 50% retracement of Wave 3 |
| Wave 5 | 100% of Wave 1, or 61.8% of Waves 1-3 |
| Wave A | 38.2%, 50%, 61.8% of Wave 5 |
| Wave B | 38.2%, 50%, 61.8% of Wave A |
| Wave C | 100%, 161.8% of Wave A |

## Timeframe Recommendations

| Timeframe | Best For | Wave Degree |
|-----------|----------|-------------|
| 1m - 5m | Scalping | Minuette |
| 15m - 1h | Day Trading | Minute |
| 4h - Daily | Swing Trading | Minor |
| Weekly | Position Trading | Intermediate |
| Monthly | Investing | Primary |

## Tips for Best Results

1. **Multiple Timeframe Analysis**: Confirm wave counts on higher timeframes
2. **Volume Confirmation**: Wave 3 typically has highest volume
3. **Oscillator Confirmation**: Use EWO for Wave 3 and divergence signals
4. **Fibonacci Clusters**: Strong support/resistance where multiple Fib levels align
5. **Pattern Completion**: Wait for wave completion signals before entering
6. **Risk Management**: Always use stops at invalidation levels

## Troubleshooting

### Indicator Not Loading
- Ensure you're using Pine Script v5
- Check for syntax errors in Pine Editor
- Try refreshing the page

### No Waves Detected
- Increase the lookback period
- Reduce pivot detection length
- Try a different timeframe

### Too Many False Signals
- Increase minimum confidence threshold
- Enable more technical filters
- Use higher timeframes

## Disclaimer

This software is for educational purposes only. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always do your own research and never trade with money you cannot afford to lose.

## Support

For issues or feature requests, please open an issue on the GitHub repository.
