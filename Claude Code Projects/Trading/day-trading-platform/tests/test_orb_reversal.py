from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_ohlcv
from src.strategies.user_strategies.orb_reversal import (
    ORBReversalStrategy,
    _hammer,
    _inverted_hammer,
    _bullish_engulfing,
    _bearish_engulfing,
)


def _assert_signal_contract(signals: pd.Series, df: pd.DataFrame) -> None:
    assert isinstance(signals, pd.Series)
    assert signals.index.equals(df.index)
    assert set(signals.unique()).issubset({-1, 0, 1})


def make_reversal_day(
    date_str: str,
    orb_high: float = 100.5,
    orb_low: float = 99.5,
    orb_volume: float = 50_000.0,
    bar_overrides: dict[int, tuple[float, float, float, float, float]] | None = None,
) -> pd.DataFrame:
    """One trading day of 1-min bars anchored to real ET market hours.

    January (EST): 9:30 AM ET = 14:30 UTC.
    Bar 0 = 9:30 AM ET (first ORB bar).
    Bar 29 = 9:59 AM ET (last ORB bar).
    Bar 30 = 10:00 AM ET (first post-ORB bar).

    bar_overrides: {bar_index: (open, high, low, close, volume)}

    ORB range is set via bar 0 (high=orb_high, low=orb_low). All other bars
    default to stable prices near the midpoint with tiny true ranges so that
    the intraday ATR is small relative to the ORB range.
    """
    n = 390
    idx = pd.date_range(f"{date_str} 14:30", periods=n, freq="1min", tz="UTC")
    mid = (orb_high + orb_low) / 2

    open_ = np.full(n, mid, dtype=float)
    high = np.full(n, mid + 0.01, dtype=float)
    low = np.full(n, mid - 0.01, dtype=float)
    close = np.full(n, mid, dtype=float)
    volume = np.full(n, orb_volume, dtype=float)

    # Bar 0 establishes the full ORB range (large TR but isolated to one bar)
    high[0] = orb_high
    low[0] = orb_low
    open_[0] = mid
    close[0] = mid

    if bar_overrides:
        for i, (o, h, l, c, v) in bar_overrides.items():
            open_[i] = o
            high[i] = h
            low[i] = l
            close[i] = c
            volume[i] = v

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


# ── Pure candle-pattern unit tests ────────────────────────────────────────────

class TestCandlePatterns:
    def test_hammer_valid(self):
        # body at 99.3-99.4, lower shadow 0.3 (3× body), upper shadow 0.02
        assert _hammer(99.3, 99.42, 99.0, 99.4)

    def test_hammer_rejects_no_lower_shadow(self):
        # lower shadow only 0.1 = 1× body — not enough
        assert not _hammer(99.3, 99.42, 99.2, 99.4)

    def test_hammer_rejects_large_upper_shadow(self):
        # upper shadow 0.4 > 0.5 × body (body=0.1) → fails
        assert not _hammer(99.3, 99.8, 99.0, 99.4)

    def test_hammer_rejects_doji(self):
        assert not _hammer(99.4, 99.8, 99.0, 99.4)  # body_size == 0

    def test_inverted_hammer_valid(self):
        # body at 100.6-100.7, upper shadow 0.25 (2.5× body), lower shadow 0.02
        assert _inverted_hammer(100.6, 100.95, 100.58, 100.7)

    def test_inverted_hammer_rejects_small_upper_shadow(self):
        assert not _inverted_hammer(100.6, 100.75, 100.58, 100.7)

    def test_bullish_engulfing_valid(self):
        # prev bearish 99.4→99.2, curr bullish 99.15→99.45 engulfs prev
        assert _bullish_engulfing(99.4, 99.2, 99.15, 99.45)

    def test_bullish_engulfing_rejects_prev_bullish(self):
        assert not _bullish_engulfing(99.2, 99.4, 99.15, 99.45)

    def test_bullish_engulfing_rejects_partial_engulf(self):
        # curr close 99.35 < prev open 99.4 → doesn't fully engulf
        assert not _bullish_engulfing(99.4, 99.2, 99.15, 99.35)

    def test_bearish_engulfing_valid(self):
        # prev bullish 100.6→100.8, curr bearish 100.85→100.55 engulfs prev
        assert _bearish_engulfing(100.6, 100.8, 100.85, 100.55)

    def test_bearish_engulfing_rejects_prev_bearish(self):
        assert not _bearish_engulfing(100.8, 100.6, 100.85, 100.55)


# ── Strategy integration tests ────────────────────────────────────────────────

# atr_multiple=0.001 bypasses the ATR filter so candle-pattern tests are isolated.
_BYPASS_ATR = {"atr_multiple": 0.001, "volume_multiplier": 1.5}


@pytest.fixture
def df() -> pd.DataFrame:
    return make_ohlcv(300)


class TestORBReversalStrategy:
    def test_returns_valid_signals(self, df):
        strat = ORBReversalStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_default_params(self):
        strat = ORBReversalStrategy()
        assert strat.params["atr_multiple"] == 1.0
        assert strat.params["volume_multiplier"] == 1.5
        assert strat.params["atr_period"] == 14

    def test_param_overrides(self):
        strat = ORBReversalStrategy(params={"atr_multiple": 1.4, "atr_period": 10})
        assert strat.params["atr_multiple"] == 1.4
        assert strat.params["atr_period"] == 10

    def test_thinkscript_body_not_empty(self):
        assert ORBReversalStrategy().thinkscript_body() != ""

    def test_eod_exit_fires_on_entry_day(self):
        """Last bar of a day that had an entry gets exit=1."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 100_000.0)},  # hammer → long entry
        )
        exits = ORBReversalStrategy(params=_BYPASS_ATR).generate_exits(df)
        assert exits.index.equals(df.index)
        assert exits.iloc[-1] == 1, "Last bar of entry day must have exit=1"

    def test_no_eod_exit_on_no_entry_day(self):
        """Days with no qualifying entry produce no exit signal."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            # No bar override → no candle pattern → no entry
        )
        exits = ORBReversalStrategy(params=_BYPASS_ATR).generate_exits(df)
        assert (exits == 0).all(), "No entry → no EOD exit"

    def test_exits_index_matches_df(self, df):
        exits = ORBReversalStrategy().generate_exits(df)
        assert exits.index.equals(df.index)

    # -- Hammer long entry --

    def test_long_entry_hammer(self):
        """Hammer below ORB low with sufficient volume → long signal."""
        # Bar 30 (10:00 AM ET): open=99.3, high=99.42, low=99.0, close=99.4
        #   body_top=99.4 < orb_low=99.5 ✓
        #   lower_shadow=0.3 >= 2×0.1 ✓  upper_shadow=0.02 <= 0.5×0.1 ✓
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 100_000.0)},
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == 1, "Expected long (+1) on hammer bar"

    def test_long_entry_hammer_in_signal_series(self):
        """generate_entries() returns 1 for the hammer bar."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 100_000.0)},
        )
        entries = ORBReversalStrategy(params=_BYPASS_ATR).generate_entries(df)
        assert entries.iloc[30] == 1

    # -- Bullish engulfing long entry --

    def test_long_entry_bullish_engulfing(self):
        """Bullish engulfing below ORB low → long signal.

        Bar 30 (first post-ORB): setup — bearish 99.4 → 99.2, body below orb_low=99.5.
        Bar 31: signal — bullish 99.15 → 99.45 engulfs bar 30; body top 99.45 < 99.5.
        (Using post-ORB bars avoids contaminating the ORB low calculation.)
        """
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={
                30: (99.4, 99.41, 99.15, 99.2, 50_000.0),    # setup: bearish below ORB low
                31: (99.15, 99.46, 99.10, 99.45, 100_000.0), # signal: bullish engulfing
            },
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[31] == 1

    # -- Inverted hammer short entry --

    def test_short_entry_inverted_hammer(self):
        """Inverted hammer above ORB high with sufficient volume → short signal."""
        # Bar 30: open=100.6, high=100.95, low=100.58, close=100.7
        #   body_bot=100.6 > orb_high=100.5 ✓
        #   upper_shadow=0.25 >= 2×0.1 ✓  lower_shadow=0.02 <= 0.5×0.1 ✓
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (100.6, 100.95, 100.58, 100.7, 100_000.0)},
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == -1, "Expected short (-1) on inverted hammer bar"

    # -- Bearish engulfing short entry --

    def test_short_entry_bearish_engulfing(self):
        """Bearish engulfing above ORB high → short signal.

        Bar 30 (first post-ORB): setup — bullish 100.6 → 100.8, body above orb_high=100.5.
        Bar 31: signal — bearish 100.85 → 100.55; body_bot=100.55 > 100.5; engulfs bar 30.
        (Using post-ORB bars avoids contaminating the ORB high calculation.)
        """
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={
                30: (100.6, 100.81, 100.59, 100.8, 50_000.0),    # setup: bullish above ORB high
                31: (100.85, 100.86, 100.54, 100.55, 100_000.0), # signal: bearish engulfing
            },
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[31] == -1

    def test_short_entry_in_short_series(self):
        """generate_short_entries() returns 1 for the inverted hammer bar."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (100.6, 100.95, 100.58, 100.7, 100_000.0)},
        )
        short = ORBReversalStrategy(params=_BYPASS_ATR).generate_short_entries(df)
        assert short.iloc[30] == 1

    # -- Volume gate --

    def test_no_signal_insufficient_volume(self):
        """Volume below threshold suppresses signal even with valid candle pattern."""
        # volume = 1.2× avg_orb_vol < 1.5× threshold
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 60_000.0)},  # 1.2× only
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == 0

    # -- Body-position gate --

    def test_no_signal_body_inside_orb(self):
        """Bar with body inside the ORB (not outside range) generates no signal."""
        # hammer-shaped candle but body straddles ORB low (body_top 99.6 > orb_low 99.5)
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.4, 99.62, 99.0, 99.6, 100_000.0)},
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == 0

    def test_no_signal_no_candle_pattern(self):
        """Bar below ORB low but not a hammer or engulfing → no signal."""
        # Large body, no wick structure → plain bearish bar, not a hammer
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.4, 99.41, 99.2, 99.25, 100_000.0)},  # bearish body, no long wick
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == 0

    # -- ATR filter --

    def test_atr_filter_skips_day_when_multiple_very_high(self):
        """atr_multiple=100 makes the filter impossible to pass — no signals."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 100_000.0)},
        )
        strat = ORBReversalStrategy(params={"atr_multiple": 100.0, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert (sigs == 0).all(), "ATR filter should block all signals"

    def test_atr_filter_passes_when_multiple_very_low(self):
        """atr_multiple=0.001 always passes — candle pattern drives the signal."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={30: (99.3, 99.42, 99.0, 99.4, 100_000.0)},
        )
        strat = ORBReversalStrategy(params={"atr_multiple": 0.001, "volume_multiplier": 1.5})
        sigs = strat.generate_signals(df)
        assert 1 in sigs.values

    # -- Multiple signals per day --

    def test_first_signal_wins_long_blocks_later_short(self):
        """Long at bar 30 fires; later inverted hammer at bar 60 is suppressed."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={
                30: (99.3, 99.42, 99.0, 99.4, 100_000.0),          # hammer → long
                60: (100.6, 100.95, 100.58, 100.7, 100_000.0),     # inv hammer → would be short
            },
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert sigs.iloc[30] == 1,  "First signal must fire"
        assert sigs.iloc[60] == 0,  "Second signal must be suppressed"

    def test_first_signal_wins_only_one_entry_per_day(self):
        """Two qualifying hammer bars on the same day: only the first fires."""
        df = make_reversal_day(
            "2024-01-02",
            orb_high=100.5, orb_low=99.5,
            orb_volume=50_000.0,
            bar_overrides={
                30: (99.3, 99.42, 99.0, 99.4, 100_000.0),
                45: (99.2, 99.32, 98.9, 99.3, 100_000.0),
            },
        )
        strat = ORBReversalStrategy(params=_BYPASS_ATR)
        sigs = strat.generate_signals(df)
        assert (sigs != 0).sum() == 1, "Exactly one signal per day"
        assert sigs.iloc[30] == 1,     "First qualifying bar fires"
        assert sigs.iloc[45] == 0,     "Second qualifying bar is suppressed"
