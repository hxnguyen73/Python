from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import volume_ratio


class ORBStrategy(BaseStrategy):
    """Opening Range Breakout — buy when price breaks above the opening range high."""

    name = "orb"

    PARAMS = {
        "range_minutes": {"type": "select", "default": 15, "options": [5, 15, 30]},
        "volume_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0, "step": 0.1},
        "stop_buffer_pct": {"type": "float", "default": 0.002, "min": 0.0, "max": 0.02, "step": 0.001},
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        range_min = self.params["range_minutes"]
        vol_mul = self.params["volume_multiplier"]
        stop_buf = self.params["stop_buffer_pct"]
        vol_ratio = volume_ratio(df)

        signal = pd.Series(0, index=df.index, dtype=int)

        # Group by date to handle each session independently
        for date, day_df in df.groupby(df.index.normalize()):
            if len(day_df) < range_min:
                continue

            orb = day_df.iloc[:range_min]
            orb_high = orb["high"].max()
            orb_low = orb["low"].min()
            post_orb = day_df.iloc[range_min:]

            for idx in post_orb.index:
                row = day_df.loc[idx]
                vr = vol_ratio.loc[idx] if idx in vol_ratio.index else 0
                if row["close"] > orb_high and vr >= vol_mul:
                    signal.loc[idx] = 1
                elif row["close"] < orb_low * (1 - stop_buf):
                    signal.loc[idx] = -1

        return signal

    def thinkscript_body(self) -> str:
        p = self.params
        return f"""\
# Opening Range Breakout Strategy
input range_minutes = {p['range_minutes']};
input volume_multiplier = {p['volume_multiplier']};
input stop_buffer_pct = {p['stop_buffer_pct']};

def isORBPeriod = SecondsFromTime(0930) < range_minutes * 60;
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
