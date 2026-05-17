from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from dotenv import load_dotenv

load_dotenv()

_TIMEFRAME_MAP: dict[str, TimeFrame] = {
    "1Min": TimeFrame(1, TimeFrameUnit.Minute),
    "5Min": TimeFrame(5, TimeFrameUnit.Minute),
    "15Min": TimeFrame(15, TimeFrameUnit.Minute),
    "30Min": TimeFrame(30, TimeFrameUnit.Minute),
    "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
    "1Day": TimeFrame(1, TimeFrameUnit.Day),
}


def _build_client() -> StockHistoricalDataClient:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise EnvironmentError(
            "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env"
        )
    return StockHistoricalDataClient(api_key, secret_key)


def fetch_bars(
    symbol: str,
    start: str | datetime,
    end: str | datetime,
    timeframe: str = "5Min",
    feed: str = "iex",
) -> pd.DataFrame:
    """Fetch OHLCV bars from Alpaca and return a normalized DataFrame.

    Returns columns: open, high, low, close, volume, vwap (when available).
    Index is a tz-aware DatetimeIndex (UTC).
    """
    client = _build_client()

    if isinstance(start, str):
        start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    if isinstance(end, str):
        end = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)

    tf = _TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe '{timeframe}'. Valid: {list(_TIMEFRAME_MAP)}")

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf,
        start=start,
        end=end,
        feed=feed,
    )

    bars = client.get_stock_bars(request)
    df = bars.df

    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # alpaca-py returns a MultiIndex (symbol, timestamp) when multiple symbols requested
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")

    df.index.name = "timestamp"
    df = df.rename(columns=str.lower)

    keep = [c for c in ["open", "high", "low", "close", "volume", "vwap"] if c in df.columns]
    return df[keep].sort_index()
