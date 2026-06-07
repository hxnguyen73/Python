from __future__ import annotations

import pandas as pd

TRADING_MODES: dict[str, dict] = {
    "Day Trade": {"timeframe": "5Min", "freq": "5T", "eod_close": True},
}


def enforce_trade_limits(
    df: pd.DataFrame,
    entries: pd.Series,
    strategy_exits: pd.Series,
    trailing_exits: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Day Trade enforcement: one entry per day, one exit per day.

    Iterates bar-by-bar within each day:
      1. If not in a position, take the first entry bar.
      2. Once in a position, take the first bar where either exit source fires.
         - strategy_exits and trailing_exits are evaluated independently.
         - Trailing stop takes precedence in labelling when both fire simultaneously.
      3. If still in position at the last bar of the day, force-close (EOD rule).
      No re-entry is allowed after an exit on the same day.

    Returns (filtered_entries, filtered_exits, exit_reasons).
    exit_reasons contains "Strategy Stop", "Trailing Stop", or "End of Day"
    at each exit bar, and "" everywhere else.
    """
    dates = _date_groups(df)
    f_entries = pd.Series(0, index=df.index, dtype=int)
    f_exits = pd.Series(0, index=df.index, dtype=int)
    exit_reasons = pd.Series("", index=df.index, dtype=object)

    in_trade = False

    for date in dates.unique():
        mask = dates == date
        day_idx = df.index[mask]
        entered_today = False

        for idx in day_idx:
            if not in_trade and not entered_today:
                if entries.loc[idx] == 1:
                    f_entries.loc[idx] = 1
                    in_trade = True
                    entered_today = True

            elif in_trade:
                has_strategy = int(strategy_exits.loc[idx]) == 1
                has_trailing = int(trailing_exits.loc[idx]) == 1
                if has_strategy or has_trailing:
                    f_exits.loc[idx] = 1
                    exit_reasons.loc[idx] = "Trailing Stop" if has_trailing else "Strategy Stop"
                    in_trade = False
                    break  # no re-entry today

        # EOD auto-close
        if in_trade:
            last_bar = day_idx[-1]
            f_exits.loc[last_bar] = 1
            exit_reasons.loc[last_bar] = "End of Day"
            in_trade = False

    return f_entries, f_exits, exit_reasons


def _date_groups(df: pd.DataFrame) -> pd.Series:
    """Return a Series of date labels aligned to df.index."""
    if hasattr(df.index, "normalize"):
        return df.index.normalize()
    return pd.DatetimeIndex([pd.Timestamp(i).normalize() for i in df.index])
