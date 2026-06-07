from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_ohlcv
from src.strategies.user_strategies.strong_trend_orb import StrongTrendORBStrategy


def _assert_signal_contract(signals: pd.Series, df: pd.DataFrame) -> None:
    assert isinstance(signals, pd.Series)
    assert signals.index.equals(df.index), "Signal index must match df index"
    assert set(signals.unique()).issubset({-1, 0, 1}), "Signals must be -1, 0, or 1"


def make_trading_day(
    date_str: str,
    open_price: float,
    orb_high: float,
    orb_low: float,
    orb_volume: float = 50_000.0,
    signal_bar_offset: int | None = None,
    signal_close: float | None = None,
    signal_volume: float | None = None,
) -> pd.DataFrame:
    """Build one trading day of 1-min bars at real ET market hours.

    January dates: 9:30 AM ET = 14:30 UTC (EST = UTC-5).
    Opening range is bars 0-29 (9:30-10:00 ET).
    Post-ORB entry window is bars 30-149 (10:00 AM–12:00 PM ET).
    signal_bar_offset is the index within the post-ORB window (0 = 10:00 AM ET bar).
    """
    n_bars = 390  # full trading day: 9:30–16:00 ET
    idx = pd.date_range(f"{date_str} 14:30", periods=n_bars, freq="1min", tz="UTC")

    close = np.full(n_bars, open_price, dtype=float)
    high = close + 0.1
    low = close - 0.1
    open_ = np.full(n_bars, open_price, dtype=float)
    volume = np.full(n_bars, orb_volume, dtype=float)

    # ORB period: bars 0-29 (9:30-9:59 ET)
    high[:30] = orb_high
    low[:30] = orb_low

    if signal_bar_offset is not None and signal_close is not None:
        bar = 30 + signal_bar_offset
        close[bar] = signal_close
        high[bar] = max(signal_close, orb_high) + 0.05
        low[bar] = min(signal_close, orb_low) - 0.05
        if signal_volume is not None:
            volume[bar] = signal_volume

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def make_two_day_gap_up(gap_pct: float = 0.01, vol_ratio: float = 2.0) -> pd.DataFrame:
    """Two-day DataFrame: day 1 baseline, day 2 gap-up with long breakout signal."""
    day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
    prev_close = day1["close"].iloc[-1]  # 100.0
    day2_open = prev_close * (1 + gap_pct)
    orb_high2 = day2_open + 0.3
    orb_vol = 50_000.0
    day2 = make_trading_day(
        "2024-01-03",
        open_price=day2_open,
        orb_high=orb_high2,
        orb_low=day2_open - 0.3,
        orb_volume=orb_vol,
        signal_bar_offset=0,
        signal_close=orb_high2 + 0.1,
        signal_volume=orb_vol * vol_ratio,
    )
    return pd.concat([day1, day2])


def make_two_day_gap_down(gap_pct: float = 0.01, vol_ratio: float = 2.0) -> pd.DataFrame:
    """Two-day DataFrame: day 1 baseline, day 2 gap-down with short breakout signal."""
    day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
    prev_close = day1["close"].iloc[-1]
    day2_open = prev_close * (1 - gap_pct)
    orb_low2 = day2_open - 0.3
    orb_vol = 50_000.0
    day2 = make_trading_day(
        "2024-01-03",
        open_price=day2_open,
        orb_high=day2_open + 0.3,
        orb_low=orb_low2,
        orb_volume=orb_vol,
        signal_bar_offset=0,
        signal_close=orb_low2 - 0.1,
        signal_volume=orb_vol * vol_ratio,
    )
    return pd.concat([day1, day2])


@pytest.fixture
def df() -> pd.DataFrame:
    return make_ohlcv(300)


class TestStrongTrendORBStrategy:
    def test_returns_valid_signals(self, df):
        strat = StrongTrendORBStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_default_params(self):
        strat = StrongTrendORBStrategy()
        assert strat.params["gap_pct_threshold"] == 0.005
        assert strat.params["volume_multiplier"] == 1.5

    def test_volume_multiplier_override(self):
        strat = StrongTrendORBStrategy(params={"volume_multiplier": 2.0})
        assert strat.params["volume_multiplier"] == 2.0

    def test_gap_threshold_override(self):
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.01})
        assert strat.params["gap_pct_threshold"] == 0.01

    def test_thinkscript_body_not_empty(self):
        assert StrongTrendORBStrategy().thinkscript_body() != ""

    def test_eod_exit_fires_on_entry_day(self):
        """Last bar of a day that had an entry gets exit=1."""
        df = make_two_day_gap_up(gap_pct=0.01, vol_ratio=2.0)
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        exits = strat.generate_exits(df)
        # Day 2 (index 390-779) had a long entry — its last bar must be an exit
        day2_exits = exits.iloc[390:]
        assert exits.index.equals(df.index)
        assert day2_exits.iloc[-1] == 1, "Last bar of entry day must have exit=1"

    def test_no_eod_exit_on_no_entry_day(self):
        """Days without an entry produce no exit signal."""
        df = make_two_day_gap_up(gap_pct=0.002)  # gap below threshold → no entry
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        exits = strat.generate_exits(df)
        assert (exits == 0).all(), "No entry → no EOD exit"

    def test_exits_index_matches_df(self, df):
        exits = StrongTrendORBStrategy().generate_exits(df)
        assert exits.index.equals(df.index)

    def test_long_entry_on_gap_up_day(self):
        """Long signal (+1) fires on gap-up day with ORB breakout and volume."""
        df = make_two_day_gap_up(gap_pct=0.01, vol_ratio=2.0)
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert 1 in sigs.values, "Expected long entry (+1) on gap-up day"
        assert -1 not in sigs.values, "No short entry expected on gap-up day"

    def test_short_entry_on_gap_down_day(self):
        """Short signal (-1) fires on gap-down day with ORB breakdown and volume."""
        df = make_two_day_gap_down(gap_pct=0.01, vol_ratio=2.0)
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert -1 in sigs.values, "Expected short entry (-1) on gap-down day"
        assert 1 not in sigs.values, "No long entry expected on gap-down day"

    def test_no_entry_when_gap_below_threshold(self):
        """No signal when gap is below the threshold (not a strong trend day)."""
        df = make_two_day_gap_up(gap_pct=0.002)  # 0.2% gap < 0.5% threshold
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005})
        sigs = strat.generate_signals(df)
        assert (sigs == 0).all(), "Gap too small — no entry expected"

    def test_no_entry_without_volume_confirmation(self):
        """No signal when breakout bar volume is below the multiplier threshold."""
        day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
        prev_close = day1["close"].iloc[-1]
        day2_open = prev_close * 1.01  # 1% gap-up
        orb_high2 = day2_open + 0.3
        orb_vol = 50_000.0
        # Signal volume is only 1.2× avg ORB volume, below 1.5× multiplier
        day2 = make_trading_day(
            "2024-01-03",
            open_price=day2_open,
            orb_high=orb_high2,
            orb_low=day2_open - 0.3,
            orb_volume=orb_vol,
            signal_bar_offset=0,
            signal_close=orb_high2 + 0.1,
            signal_volume=orb_vol * 1.2,  # below 1.5× threshold
        )
        df = pd.concat([day1, day2])
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert (sigs == 0).all(), "Volume too low — no entry expected"

    def test_no_entry_after_time_cutoff(self):
        """No signal when breakout occurs at or after 12:00 PM ET (bar offset 120+)."""
        day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
        prev_close = day1["close"].iloc[-1]
        day2_open = prev_close * 1.01
        orb_high2 = day2_open + 0.3
        orb_vol = 50_000.0
        # Bar offset 120 = 12:00 PM ET bar — outside the entry window (after 9:00 AM PST)
        day2 = make_trading_day(
            "2024-01-03",
            open_price=day2_open,
            orb_high=orb_high2,
            orb_low=day2_open - 0.3,
            orb_volume=orb_vol,
            signal_bar_offset=120,  # 12:00 PM ET — after cutoff
            signal_close=orb_high2 + 0.1,
            signal_volume=orb_vol * 2.0,
        )
        df = pd.concat([day1, day2])
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert (sigs == 0).all(), "Entry after 12:00 PM ET must be ignored"

    def test_at_most_one_entry_per_day(self):
        """Only the first qualifying breakout bar fires; subsequent bars on same day are 0."""
        day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
        prev_close = day1["close"].iloc[-1]
        day2_open = prev_close * 1.01
        orb_high2 = day2_open + 0.3
        orb_vol = 50_000.0
        day2 = make_trading_day(
            "2024-01-03",
            open_price=day2_open,
            orb_high=orb_high2,
            orb_low=day2_open - 0.3,
            orb_volume=orb_vol,
            signal_bar_offset=0,
            signal_close=orb_high2 + 0.1,
            signal_volume=orb_vol * 2.0,
        )
        df = pd.concat([day1, day2])
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert (sigs == 1).sum() == 1, "Exactly one long entry per day"

    def test_generate_entries_long_only(self):
        """generate_entries() returns 1 only for long entries, never for short."""
        df = make_two_day_gap_up(gap_pct=0.01, vol_ratio=2.0)
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        entries = strat.generate_entries(df)
        assert set(entries.unique()).issubset({0, 1})
        assert 1 in entries.values

    def test_generate_short_entries(self):
        """generate_short_entries() returns 1 on short-entry bars, 0 elsewhere."""
        df = make_two_day_gap_down(gap_pct=0.01, vol_ratio=2.0)
        strat = StrongTrendORBStrategy(params={"gap_pct_threshold": 0.005, "volume_multiplier": 1.5})
        short_entries = strat.generate_short_entries(df)
        assert set(short_entries.unique()).issubset({0, 1})
        assert 1 in short_entries.values

    def test_first_day_skipped_no_prev_close(self):
        """Single-day data produces no entries (no previous close to compute gap)."""
        day1 = make_trading_day("2024-01-02", open_price=100.0, orb_high=100.5, orb_low=99.5)
        strat = StrongTrendORBStrategy()
        sigs = strat.generate_signals(day1)
        assert (sigs == 0).all(), "First day has no prev close — no entries"
