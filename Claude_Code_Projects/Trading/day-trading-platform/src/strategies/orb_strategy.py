from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import volume_ratio

_ORB_MINUTES = 30  # fixed opening range: 9:30 – 10:00 ET


class ORBStrategy(BaseStrategy):
    """Opening Range Breakout — 30-minute opening range, time-based."""

    name = "orb"

    PARAMS = {
        "volume_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0, "step": 0.1},
        "stop_buffer_pct": {"type": "float", "default": 0.002, "min": 0.0, "max": 0.02, "step": 0.001},
    }

    def _compute_orb(self, df: pd.DataFrame, vol_ratio: pd.Series):
        vol_mul = self.params["volume_multiplier"]
        stop_buf = self.params["stop_buffer_pct"]

        entries = pd.Series(0, index=df.index, dtype=int)
        exits = pd.Series(0, index=df.index, dtype=int)

        # Ensure index is timezone-aware for ET conversion
        idx = df.index
        if idx.tz is None:
            idx = idx.tz_localize("UTC")

        et_index = idx.tz_convert("America/New_York")

        for date, day_df in df.groupby(df.index.normalize()):
            if day_df.empty:
                continue

            # ET timestamps for this day's bars
            day_et = et_index[df.index.normalize() == date]

            # Opening range: 9:30 AM to 9:30 AM + 30 min ET
            first_et = day_et[0]
            market_open_et = first_et.replace(hour=9, minute=30, second=0, microsecond=0)
            orb_end_et = market_open_et + pd.Timedelta(minutes=_ORB_MINUTES)

            orb_mask = day_et < orb_end_et
            post_mask = day_et >= orb_end_et

            day_utc = day_df.index
            orb = day_df.loc[day_utc[orb_mask]]
            post_orb = day_df.loc[day_utc[post_mask]]

            if orb.empty or post_orb.empty:
                continue

            orb_high = orb["high"].max()
            orb_low = orb["low"].min()

            for idx_bar in post_orb.index:
                row = day_df.loc[idx_bar]
                vr = vol_ratio.loc[idx_bar] if idx_bar in vol_ratio.index else 0
                if row["close"] > orb_high and vr >= vol_mul:
                    entries.loc[idx_bar] = 1
                elif row["close"] < orb_low * (1 - stop_buf):
                    exits.loc[idx_bar] = 1

        return entries, exits

    def generate_entries(self, df: pd.DataFrame) -> pd.Series:
        vr = volume_ratio(df)
        entries, _ = self._compute_orb(df, vr)
        return entries

    def generate_exits(self, df: pd.DataFrame) -> pd.Series:
        vr = volume_ratio(df)
        _, exits = self._compute_orb(df, vr)
        return exits

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        entries = self.generate_entries(df)
        exits = self.generate_exits(df)
        signal = pd.Series(0, index=df.index, dtype=int)
        signal[entries == 1] = 1
        signal[exits == 1] = -1
        return signal

    def thinkscript_body(self) -> str:
        p = self.params
        return f"""\
# Opening Range Breakout — 30-minute range (9:30–10:00 ET)
input volume_multiplier = {p['volume_multiplier']};
input stop_buffer_pct = {p['stop_buffer_pct']};

def isORBPeriod = SecondsFromTime(0930) < 1800;  # 30 minutes
def orbHigh = HighestAll(if isORBPeriod then high else 0);
def orbLow = LowestAll(if isORBPeriod then low else Double.POSITIVE_INFINITY);
def volAvg = Average(volume, 20);

def entrySignal = !isORBPeriod and close > orbHigh and volume >= volAvg * volume_multiplier;
def exitSignal = !isORBPeriod and close < orbLow * (1 - stop_buffer_pct);

Alert(entrySignal, "ORB Breakout Entry", Alert.BAR, Sound.Chime);
Alert(exitSignal, "ORB Stop Hit", Alert.BAR, Sound.Ring);
AddChartBubble(entrySignal, low, "▲", Color.GREEN, no);
AddChartBubble(exitSignal, high, "▼", Color.RED, yes);
plot ORBHigh = orbHigh;
ORBHigh.SetDefaultColor(Color.GREEN);
plot ORBLow = orbLow;
ORBLow.SetDefaultColor(Color.RED);
AddCloud(orbHigh, orbLow, Color.DARK_GREEN, Color.DARK_RED);
"""
