from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import vwap, volume_ratio


class VWAPStrategy(BaseStrategy):
    """VWAP reversion/breakout: entry when price crosses above VWAP with a volume spike."""

    name = "vwap"

    PARAMS = {
        "vwap_buffer_pct": {"type": "float", "default": 0.001, "min": 0.0, "max": 0.01, "step": 0.0001},
        "volume_multiplier": {"type": "float", "default": 1.8, "min": 1.0, "max": 5.0, "step": 0.1},
        "stop_pct": {"type": "float", "default": 0.005, "min": 0.001, "max": 0.05, "step": 0.001},
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        vwap_line = vwap(df)
        vol_ratio = volume_ratio(df)
        buffer = self.params["vwap_buffer_pct"]
        vol_mul = self.params["volume_multiplier"]

        above_vwap = df["close"] > vwap_line * (1 + buffer)
        was_below = df["close"].shift(1) <= vwap_line.shift(1)
        vol_spike = vol_ratio >= vol_mul

        entry = above_vwap & was_below & vol_spike
        exit_ = df["close"] < vwap_line * (1 - buffer)

        signal = pd.Series(0, index=df.index, dtype=int)
        signal[entry] = 1
        signal[exit_] = -1
        return signal

    def thinkscript_body(self) -> str:
        buf = self.params["vwap_buffer_pct"]
        vol = self.params["volume_multiplier"]
        stop = self.params["stop_pct"]
        return f"""\
# VWAP Reversion/Breakout Strategy
input vwap_buffer_pct = {buf};
input volume_multiplier = {vol};
input stop_pct = {stop};

def v = TotalSum(HL2 * volume) / TotalSum(volume);
def volAvg = Average(volume, 20);
def aboveVWAP = close > v * (1 + vwap_buffer_pct);
def wasBelowVWAP = close[1] <= v[1];
def volSpike = volume >= volAvg * volume_multiplier;

def entrySignal = aboveVWAP and wasBelowVWAP and volSpike;
def exitSignal = close < v * (1 - vwap_buffer_pct);

Alert(entrySignal, "VWAP Entry", Alert.BAR, Sound.Chime);
Alert(exitSignal, "VWAP Exit", Alert.BAR, Sound.Ring);
AddChartBubble(entrySignal, low, "▲", Color.GREEN, no);
AddChartBubble(exitSignal, high, "▼", Color.RED, yes);
plot VWAPLine = v;
VWAPLine.SetDefaultColor(Color.YELLOW);
AddCloud(v * (1 + vwap_buffer_pct), v * (1 - vwap_buffer_pct), Color.DARK_GREEN, Color.DARK_RED);
"""
