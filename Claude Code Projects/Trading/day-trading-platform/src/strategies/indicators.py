from __future__ import annotations

from typing import NamedTuple

import pandas as pd


def vwap(df: pd.DataFrame) -> pd.Series:
    """Session VWAP — resets at midnight UTC (works with intraday bars)."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    date_group = df.index.normalize() if hasattr(df.index, "normalize") else df.index.date
    cum_tp_vol = (typical * df["volume"]).groupby(date_group).cumsum()
    cum_vol = df["volume"].groupby(date_group).cumsum()
    return (cum_tp_vol / cum_vol).rename("vwap")


def ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    return df[column].ewm(span=period, adjust=False).mean().rename(f"ema_{period}")


class MACDResult(NamedTuple):
    macd: pd.Series
    signal: pd.Series
    histogram: pd.Series


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> MACDResult:
    fast_ema = df["close"].ewm(span=fast, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = (fast_ema - slow_ema).rename("macd")
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean().rename("signal")
    histogram = (macd_line - signal_line).rename("histogram")
    return MACDResult(macd_line, signal_line, histogram)


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return (100 - 100 / (1 + rs)).rename("rsi")


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean().rename("atr")


def volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Current volume divided by rolling-average volume."""
    avg = df["volume"].rolling(period).mean()
    return (df["volume"] / avg).rename("volume_ratio")
