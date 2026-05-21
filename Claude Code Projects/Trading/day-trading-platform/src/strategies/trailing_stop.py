from __future__ import annotations

import pandas as pd


def apply_trailing_stop(
    df: pd.DataFrame,
    entries: pd.Series,
    stop_pct: float,
) -> pd.Series:
    """Compute bar-close trailing stop exit signals.

    On each entry bar: initial stop = close * (1 - stop_pct).
    On each subsequent bar: if close rises above the prior high-water mark,
    the stop is raised to new_high * (1 - stop_pct).
    Exit fires when close <= trailing_stop.

    Returns a Series with 1 where the trailing stop is hit, 0 otherwise.
    Multiple positions are not tracked — a new entry resets the stop.
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
            # Ratchet stop up if price made a new close high
            if close > high_water:
                high_water = close
                trailing_stop = high_water * (1 - stop_pct)

            # Check whether stop is hit on this bar's close
            if close <= trailing_stop:
                stop_exits.loc[idx] = 1
                in_trade = False
                high_water = 0.0
                trailing_stop = 0.0

            # If a new entry fires while in a trade, reset stop to new entry price
            if is_entry:
                high_water = close
                trailing_stop = close * (1 - stop_pct)

    return stop_exits
