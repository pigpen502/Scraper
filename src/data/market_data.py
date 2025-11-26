"""Market data fetching and management for Elliott Wave Trading Bot."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from ..utils.helpers import get_lookback_period, timeframe_to_interval
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataFetcher:
    """Fetches and manages market data from various sources."""

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize the market data fetcher.

        Args:
            cache_enabled: Whether to cache fetched data
        """
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)

    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a symbol.

        Args:
            symbol: Stock/asset symbol
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk)
            period: Lookback period (e.g., '1y', '6mo', '1mo')
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{timeframe}_{period}_{start_date}_{end_date}"

        # Check cache
        if self.cache_enabled and self._is_cache_valid(cache_key):
            logger.debug(f"Returning cached data for {symbol}")
            return self._cache[cache_key].copy()

        logger.info(f"Fetching historical data for {symbol} ({timeframe})")

        try:
            ticker = yf.Ticker(symbol)
            interval = timeframe_to_interval(timeframe)

            # Determine how to fetch data
            if start_date and end_date:
                df = ticker.history(
                    start=start_date, end=end_date, interval=interval
                )
            elif period:
                df = ticker.history(period=period, interval=interval)
            else:
                # Use default lookback based on timeframe
                default_period = get_lookback_period(timeframe)
                df = ticker.history(period=default_period, interval=interval)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Standardize column names
            df = self._standardize_dataframe(df)

            # Cache the data
            if self.cache_enabled:
                self._cache[cache_key] = df.copy()
                self._cache_timestamps[cache_key] = datetime.now()

            logger.info(f"Fetched {len(df)} bars for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def get_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        period: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols.

        Args:
            symbols: List of symbols
            timeframe: Timeframe
            period: Lookback period

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}

        for symbol in symbols:
            data = self.get_historical_data(
                symbol=symbol, timeframe=timeframe, period=period
            )
            if not data.empty:
                results[symbol] = data

        return results

    def get_realtime_price(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time price information for a symbol.

        Args:
            symbol: Stock/asset symbol

        Returns:
            Dictionary with price info or None
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "price": info.get("regularMarketPrice", info.get("currentPrice")),
                "open": info.get("regularMarketOpen"),
                "high": info.get("regularMarketDayHigh"),
                "low": info.get("regularMarketDayLow"),
                "volume": info.get("regularMarketVolume"),
                "previous_close": info.get("previousClose"),
                "timestamp": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Error fetching real-time price for {symbol}: {e}")
            return None

    def get_ticker_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed information about a ticker.

        Args:
            symbol: Stock/asset symbol

        Returns:
            Dictionary with ticker info
        """
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except Exception as e:
            logger.error(f"Error fetching ticker info for {symbol}: {e}")
            return None

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame column names and format.

        Args:
            df: Raw DataFrame from yfinance

        Returns:
            Standardized DataFrame
        """
        # Ensure consistent column names
        column_mapping = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Adj Close": "adj_close",
        }

        df = df.rename(columns=column_mapping)

        # Ensure we have the required columns
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Missing column: {col}")

        # Remove any rows with NaN in critical columns
        df = df.dropna(subset=["open", "high", "low", "close"])

        return df

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache:
            return False

        cache_time = self._cache_timestamps.get(cache_key)
        if cache_time is None:
            return False

        return datetime.now() - cache_time < self._cache_ttl

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached data.

        Args:
            symbol: Specific symbol to clear, or None for all
        """
        if symbol:
            keys_to_remove = [k for k in self._cache if k.startswith(symbol)]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

        logger.debug(f"Cache cleared for: {symbol or 'all'}")
