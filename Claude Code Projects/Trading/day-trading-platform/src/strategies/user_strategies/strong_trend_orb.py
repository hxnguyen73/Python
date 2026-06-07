from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy

_ORB_MINUTES = 30        # 9:30–10:00 ET opening range
_ENTRY_WINDOW_MINUTES = 150  # entries allowed until 12:00 PM ET / 9:00 AM PST


class StrongTrendORBStrategy(BaseStrategy):
    """ORB entry on strong gap days with opening-range volume confirmation.

    A day qualifies as a strong trend day when the overnight gap exceeds
    gap_pct_threshold (default 0.5%):
      gap-up  (+gap)  → scan for long  breakout above the 30-min ORB high
      gap-down (-gap) → scan for short breakout below the 30-min ORB low

    The breakout bar's volume must be at least volume_multiplier × the mean
    volume of the 6 bars in the opening range (9:30–10:00 ET).

    Entry window: 10:00 AM – 12:00 PM ET only (after 9:00 AM PST no new entries).
    First qualifying breakout per day is taken; no reversal entries same day.

    generate_signals() convention (deviates from base for bidirectionality):
        +1 = long entry  (gap-up breakout)
        -1 = short entry (gap-down breakdown)
         0 = no signal

    Use generate_entries()       for long-only VectorBT compatibility.
    Use generate_short_entries() for short-side entries as a separate Series.
    """

    name = "strong_trend_orb"

    PARAMS = {
        "gap_pct_threshold": {
            "type": "float",
            "default": 0.005,
            "min": 0.001,
            "max": 0.03,
            "step": 0.001,
        },
        "volume_multiplier": {
            "type": "float",
            "default": 1.5,
            "min": 1.25,
            "max": 2.0,
            "step": 0.05,
        },
    }

    def _compute_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index, dtype=int)

        idx = df.index
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        et_index = idx.tz_convert("America/New_York")

        vol_mul = self.params["volume_multiplier"]
        gap_thresh = self.params["gap_pct_threshold"]

        prev_day_close: float | None = None

        for date, day_df in df.groupby(df.index.normalize()):
            if day_df.empty:
                continue

            day_et = et_index[df.index.normalize() == date]

            # First day only anchors prev_day_close — no entry possible
            if prev_day_close is None:
                prev_day_close = day_df["close"].iloc[-1]
                continue

            day_open = day_df["open"].iloc[0]
            gap_pct = (day_open - prev_day_close) / prev_day_close
            prev_day_close = day_df["close"].iloc[-1]

            if gap_pct >= gap_thresh:
                direction = 1    # gap-up: look for long breakout
            elif gap_pct <= -gap_thresh:
                direction = -1   # gap-down: look for short breakdown
            else:
                continue         # gap too small — not a strong trend day

            # Anchor ORB start to 9:30 AM ET regardless of first bar time
            market_open_et = day_et[0].replace(hour=9, minute=30, second=0, microsecond=0)
            orb_end_et = market_open_et + pd.Timedelta(minutes=_ORB_MINUTES)
            entry_cutoff_et = market_open_et + pd.Timedelta(minutes=_ENTRY_WINDOW_MINUTES)

            orb_mask = day_et < orb_end_et
            post_mask = (day_et >= orb_end_et) & (day_et < entry_cutoff_et)

            day_utc = day_df.index
            orb_df = day_df.loc[day_utc[orb_mask]]
            post_df = day_df.loc[day_utc[post_mask]]

            if orb_df.empty or post_df.empty:
                continue

            orb_high = orb_df["high"].max()
            orb_low = orb_df["low"].min()
            avg_orb_vol = orb_df["volume"].mean()

            # Scan post-ORB bars; first breakout with volume confirmation wins
            for bar_idx in post_df.index:
                row = post_df.loc[bar_idx]
                vol_ok = row["volume"] >= vol_mul * avg_orb_vol

                if direction == 1 and row["close"] > orb_high and vol_ok:
                    signals.loc[bar_idx] = 1
                    break
                elif direction == -1 and row["close"] < orb_low and vol_ok:
                    signals.loc[bar_idx] = -1
                    break

        return signals

    def generate_entries(self, df: pd.DataFrame) -> pd.Series:
        """Long entries only (signal == +1). Short side: use generate_short_entries()."""
        return (self._compute_signals(df) == 1).astype(int)

    def generate_short_entries(self, df: pd.DataFrame) -> pd.Series:
        """Short entry bars, returned as 1 where a short entry is signaled."""
        return (self._compute_signals(df) == -1).astype(int)

    def generate_exits(self, df: pd.DataFrame) -> pd.Series:
        """Force-close any open position at the last bar of any day with an entry."""
        exits = pd.Series(0, index=df.index, dtype=int)
        signals = self._compute_signals(df)
        for _date, day_df in df.groupby(df.index.normalize()):
            if (signals.loc[day_df.index] != 0).any():
                exits.loc[day_df.index[-1]] = 1
        return exits

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return self._compute_signals(df)

    def thinkscript_body(self) -> str:
        p = self.params
        return f"""\
# Strong Trend ORB Entry — gap-day opening range breakout with volume confirmation
# Apply on a 5-minute chart. Designed for single-day charts in ThinkorSwim.
input gap_pct_threshold = {p['gap_pct_threshold']};
input volume_multiplier = {p['volume_multiplier']};

# Gap: today's open vs previous session close
def prevDayClose = close(period = "DAY")[1];
def todayOpen = open(period = "DAY");
def gapPct = (todayOpen - prevDayClose) / prevDayClose;
def isGapUpDay = gapPct >= gap_pct_threshold;
def isGapDownDay = gapPct <= -gap_pct_threshold;

# Opening range: 9:30–10:00 ET (30 minutes = 1800 seconds from open)
def isORBPeriod = SecondsFromTime(0930) < 1800;

# Entry window: 10:00 AM–12:00 PM ET (after 9:00 AM PST, no new entries)
def isEntryWindow = !isORBPeriod and SecondsFromTime(0930) < 9000;

# Opening range bounds
def orbHigh = HighestAll(if isORBPeriod then high else 0);
def orbLow = LowestAll(if isORBPeriod then low else Double.POSITIVE_INFINITY);

# Average volume during the 30-minute opening range
def orbVolumeSum = TotalSum(if isORBPeriod then volume else 0);
def orbBarCount = TotalSum(if isORBPeriod then 1 else 0);
def avgORBVolume = if orbBarCount > 0 then orbVolumeSum / orbBarCount else Double.NaN;

# Entry conditions
def longEntry = isGapUpDay and isEntryWindow
    and close > orbHigh
    and volume >= volume_multiplier * avgORBVolume;
def shortEntry = isGapDownDay and isEntryWindow
    and close < orbLow
    and volume >= volume_multiplier * avgORBVolume;

Alert(longEntry, "Strong Trend ORB Long Entry", Alert.BAR, Sound.Chime);
Alert(shortEntry, "Strong Trend ORB Short Entry", Alert.BAR, Sound.Bell);
AddChartBubble(longEntry, low, "\\u25b2 Long", Color.GREEN, no);
AddChartBubble(shortEntry, high, "\\u25bc Short", Color.RED, yes);

plot ORBHigh = orbHigh;
ORBHigh.SetDefaultColor(Color.GREEN);
ORBHigh.SetStyle(Curve.LONG_DASH);
plot ORBLow = orbLow;
ORBLow.SetDefaultColor(Color.RED);
ORBLow.SetStyle(Curve.LONG_DASH);
AddCloud(orbHigh, orbLow, Color.DARK_GREEN, Color.DARK_RED);
"""
