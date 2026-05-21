from __future__ import annotations

import pandas as pd


def apply_trailing_stop(
    df: pd.DataFrame,
    entries: pd.Series,
    stop_pct: float,
) -> pd.Series:
    """Fixed-percentage bar-close trailing stop.

    On entry: stop = close * (1 - stop_pct), high_water = close.
    Each bar: if close > high_water, raise stop to new_high * (1 - stop_pct).
    Exit when close <= stop.
    """
    stop_exits = pd.Series(0, index=df.index, dtype=int)
    if stop_pct <= 0:
        return stop_exits

    in_trade = False
    high_water = 0.0
    trailing_stop = 0.0

    for idx in df.index:
        close = float(df.loc[idx, "close"])
        is_entry = int(entries.loc[idx]) == 1

        if not in_trade:
            if is_entry:
                in_trade = True
                high_water = close
                trailing_stop = close * (1 - stop_pct)
        else:
            if close > high_water:
                high_water = close
                trailing_stop = high_water * (1 - stop_pct)
            if close <= trailing_stop:
                stop_exits.loc[idx] = 1
                in_trade = False
                high_water = 0.0
                trailing_stop = 0.0
            if is_entry:
                high_water = close
                trailing_stop = close * (1 - stop_pct)

    return stop_exits


def apply_atr_trailing_stop(
    df: pd.DataFrame,
    entries: pd.Series,
    atr_period: int,
    atr_multiplier: float,
) -> pd.Series:
    """ATR-based bar-close trailing stop.

    On entry: stop = close - multiplier * ATR, high_water = close.
    Each bar: if close > high_water, compute new candidate stop
    (close - multiplier * ATR) and ratchet the stop up to the higher value.
    Exit when close <= stop.
    """
    from src.strategies.indicators import atr as compute_atr

    stop_exits = pd.Series(0, index=df.index, dtype=int)
    if atr_multiplier <= 0:
        return stop_exits

    atr_series = compute_atr(df, atr_period)

    in_trade = False
    high_water = 0.0
    trailing_stop = 0.0

    for idx in df.index:
        close = float(df.loc[idx, "close"])
        atr_val = float(atr_series.loc[idx]) if not pd.isna(atr_series.loc[idx]) else 0.0
        is_entry = int(entries.loc[idx]) == 1

        if not in_trade:
            if is_entry and atr_val > 0:
                in_trade = True
                high_water = close
                trailing_stop = close - atr_multiplier * atr_val
        else:
            if close > high_water:
                high_water = close
                # Only ratchet up, never down
                candidate = close - atr_multiplier * atr_val
                trailing_stop = max(trailing_stop, candidate)

            if close <= trailing_stop:
                stop_exits.loc[idx] = 1
                in_trade = False
                high_water = 0.0
                trailing_stop = 0.0

            if is_entry and atr_val > 0:
                high_water = close
                trailing_stop = close - atr_multiplier * atr_val

    return stop_exits
