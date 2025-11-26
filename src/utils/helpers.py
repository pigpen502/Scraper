"""Helper utilities for Elliott Wave Trading Bot."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


def calculate_percentage_change(start: float, end: float) -> float:
    """Calculate percentage change between two values."""
    if start == 0:
        return 0.0
    return ((end - start) / abs(start)) * 100


def find_local_extrema(
    data: pd.Series, order: int = 5
) -> Tuple[List[int], List[int]]:
    """
    Find local maxima and minima in a series.

    Args:
        data: Price series
        order: Number of points on each side to compare

    Returns:
        Tuple of (maxima_indices, minima_indices)
    """
    maxima = []
    minima = []

    for i in range(order, len(data) - order):
        # Check for local maximum
        if all(data.iloc[i] > data.iloc[i - j] for j in range(1, order + 1)) and all(
            data.iloc[i] > data.iloc[i + j] for j in range(1, order + 1)
        ):
            maxima.append(i)

        # Check for local minimum
        if all(data.iloc[i] < data.iloc[i - j] for j in range(1, order + 1)) and all(
            data.iloc[i] < data.iloc[i + j] for j in range(1, order + 1)
        ):
            minima.append(i)

    return maxima, minima


def fibonacci_retracement_levels(
    high: float, low: float, direction: str = "up"
) -> dict:
    """
    Calculate Fibonacci retracement levels.

    Args:
        high: High price
        low: Low price
        direction: 'up' for bullish, 'down' for bearish

    Returns:
        Dictionary of Fibonacci levels
    """
    diff = high - low
    levels = {
        "0.0": 0.0,
        "0.236": 0.236,
        "0.382": 0.382,
        "0.5": 0.5,
        "0.618": 0.618,
        "0.786": 0.786,
        "1.0": 1.0,
    }

    if direction == "up":
        return {k: high - (v * diff) for k, v in levels.items()}
    else:
        return {k: low + (v * diff) for k, v in levels.items()}


def fibonacci_extension_levels(
    wave1_start: float, wave1_end: float, wave2_end: float
) -> dict:
    """
    Calculate Fibonacci extension levels for Wave 3 projections.

    Args:
        wave1_start: Start of Wave 1
        wave1_end: End of Wave 1
        wave2_end: End of Wave 2 (retracement)

    Returns:
        Dictionary of extension levels
    """
    wave1_length = abs(wave1_end - wave1_start)
    direction = 1 if wave1_end > wave1_start else -1

    extensions = {
        "1.0": 1.0,
        "1.272": 1.272,
        "1.618": 1.618,
        "2.0": 2.0,
        "2.618": 2.618,
        "3.618": 3.618,
    }

    return {k: wave2_end + (direction * v * wave1_length) for k, v in extensions.items()}


def calculate_atr(
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


def timeframe_to_interval(timeframe: str) -> str:
    """
    Convert timeframe string to yfinance interval format.

    Args:
        timeframe: Timeframe string (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk)

    Returns:
        yfinance compatible interval string
    """
    mapping = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "60m",
        "4h": "60m",  # yfinance doesn't support 4h directly
        "1d": "1d",
        "1wk": "1wk",
    }
    return mapping.get(timeframe, "1d")


def get_lookback_period(timeframe: str) -> str:
    """
    Get appropriate lookback period for a timeframe.

    Args:
        timeframe: Trading timeframe

    Returns:
        Period string for yfinance
    """
    mapping = {
        "1m": "7d",
        "5m": "60d",
        "15m": "60d",
        "30m": "60d",
        "1h": "730d",
        "4h": "730d",
        "1d": "2y",
        "1wk": "5y",
    }
    return mapping.get(timeframe, "1y")
