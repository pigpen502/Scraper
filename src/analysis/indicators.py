"""Technical indicators for Elliott Wave Trading Bot."""

from typing import Optional, Tuple

import numpy as np
import pandas as pd

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """
    Technical indicators to complement Elliott Wave analysis.

    These indicators help confirm wave counts and identify entry/exit points.
    """

    @staticmethod
    def rsi(
        close: pd.Series, period: int = 14, overbought: float = 70, oversold: float = 30
    ) -> pd.DataFrame:
        """
        Calculate Relative Strength Index.

        Args:
            close: Close prices
            period: RSI period
            overbought: Overbought threshold
            oversold: Oversold threshold

        Returns:
            DataFrame with RSI and signals
        """
        delta = close.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        result = pd.DataFrame(
            {
                "rsi": rsi,
                "overbought": overbought,
                "oversold": oversold,
                "signal": pd.Series("neutral", index=close.index),
            }
        )

        result.loc[rsi > overbought, "signal"] = "overbought"
        result.loc[rsi < oversold, "signal"] = "oversold"

        return result

    @staticmethod
    def macd(
        close: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            close: Close prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            DataFrame with MACD, signal, and histogram
        """
        fast_ema = close.ewm(span=fast_period, adjust=False).mean()
        slow_ema = close.ewm(span=slow_period, adjust=False).mean()

        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame(
            {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
            }
        )

    @staticmethod
    def bollinger_bands(
        close: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> pd.DataFrame:
        """
        Calculate Bollinger Bands.

        Args:
            close: Close prices
            period: Moving average period
            std_dev: Number of standard deviations

        Returns:
            DataFrame with upper, middle, lower bands and bandwidth
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        bandwidth = (upper - lower) / middle * 100
        percent_b = (close - lower) / (upper - lower)

        return pd.DataFrame(
            {
                "upper": upper,
                "middle": middle,
                "lower": lower,
                "bandwidth": bandwidth,
                "percent_b": percent_b,
            }
        )

    @staticmethod
    def atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period

        Returns:
            ATR series
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3,
    ) -> pd.DataFrame:
        """
        Calculate Stochastic Oscillator.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            k_period: %K period
            d_period: %D period

        Returns:
            DataFrame with %K and %D
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return pd.DataFrame({"k": k, "d": d})

    @staticmethod
    def ema(close: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return close.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(close: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return close.rolling(window=period).mean()

    @staticmethod
    def volume_profile(
        close: pd.Series, volume: pd.Series, period: int = 20
    ) -> pd.DataFrame:
        """
        Calculate Volume-Weighted Average Price and volume indicators.

        Args:
            close: Close prices
            volume: Volume data
            period: Calculation period

        Returns:
            DataFrame with VWAP and volume metrics
        """
        typical_price = close
        vwap = (typical_price * volume).rolling(window=period).sum() / volume.rolling(
            window=period
        ).sum()

        avg_volume = volume.rolling(window=period).mean()
        volume_ratio = volume / avg_volume

        return pd.DataFrame(
            {
                "vwap": vwap,
                "avg_volume": avg_volume,
                "volume_ratio": volume_ratio,
            }
        )

    @staticmethod
    def momentum(close: pd.Series, period: int = 10) -> pd.Series:
        """
        Calculate Momentum indicator.

        Args:
            close: Close prices
            period: Momentum period

        Returns:
            Momentum series
        """
        return close - close.shift(period)

    @staticmethod
    def wave_oscillator(close: pd.Series) -> pd.DataFrame:
        """
        Calculate Elliott Wave Oscillator (5-35 EMA difference).

        This oscillator helps identify Wave 3 (strongest) and divergences.

        Args:
            close: Close prices

        Returns:
            DataFrame with oscillator and signals
        """
        ema_5 = close.ewm(span=5, adjust=False).mean()
        ema_35 = close.ewm(span=35, adjust=False).mean()

        oscillator = ema_5 - ema_35

        # Detect divergences
        result = pd.DataFrame(
            {
                "oscillator": oscillator,
                "ema_5": ema_5,
                "ema_35": ema_35,
                "zero_cross": np.sign(oscillator).diff().fillna(0),
            }
        )

        return result

    @staticmethod
    def fibonacci_retracement_indicator(
        high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 50
    ) -> pd.DataFrame:
        """
        Calculate dynamic Fibonacci retracement levels.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            lookback: Lookback period for swing high/low

        Returns:
            DataFrame with Fibonacci levels
        """
        rolling_high = high.rolling(window=lookback).max()
        rolling_low = low.rolling(window=lookback).min()

        diff = rolling_high - rolling_low

        fib_levels = {
            "high": rolling_high,
            "low": rolling_low,
            "fib_236": rolling_high - 0.236 * diff,
            "fib_382": rolling_high - 0.382 * diff,
            "fib_500": rolling_high - 0.5 * diff,
            "fib_618": rolling_high - 0.618 * diff,
            "fib_786": rolling_high - 0.786 * diff,
        }

        return pd.DataFrame(fib_levels)

    @staticmethod
    def calculate_all(
        df: pd.DataFrame,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        atr_period: int = 14,
    ) -> pd.DataFrame:
        """
        Calculate all indicators and add to DataFrame.

        Args:
            df: OHLCV DataFrame
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            bb_period: Bollinger Bands period
            atr_period: ATR period

        Returns:
            DataFrame with all indicators
        """
        result = df.copy()

        # RSI
        rsi_df = TechnicalIndicators.rsi(df["close"], period=rsi_period)
        result["rsi"] = rsi_df["rsi"]

        # MACD
        macd_df = TechnicalIndicators.macd(
            df["close"], fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal
        )
        result["macd"] = macd_df["macd"]
        result["macd_signal"] = macd_df["signal"]
        result["macd_histogram"] = macd_df["histogram"]

        # Bollinger Bands
        bb_df = TechnicalIndicators.bollinger_bands(df["close"], period=bb_period)
        result["bb_upper"] = bb_df["upper"]
        result["bb_middle"] = bb_df["middle"]
        result["bb_lower"] = bb_df["lower"]
        result["bb_percent"] = bb_df["percent_b"]

        # ATR
        result["atr"] = TechnicalIndicators.atr(
            df["high"], df["low"], df["close"], period=atr_period
        )

        # Stochastic
        stoch_df = TechnicalIndicators.stochastic(df["high"], df["low"], df["close"])
        result["stoch_k"] = stoch_df["k"]
        result["stoch_d"] = stoch_df["d"]

        # Elliott Wave Oscillator
        ewo_df = TechnicalIndicators.wave_oscillator(df["close"])
        result["wave_oscillator"] = ewo_df["oscillator"]

        # EMAs
        result["ema_9"] = TechnicalIndicators.ema(df["close"], 9)
        result["ema_21"] = TechnicalIndicators.ema(df["close"], 21)
        result["ema_50"] = TechnicalIndicators.ema(df["close"], 50)
        result["ema_200"] = TechnicalIndicators.ema(df["close"], 200)

        return result
