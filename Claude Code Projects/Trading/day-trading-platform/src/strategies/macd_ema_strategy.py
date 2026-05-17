from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import ema, macd


class MACDEMAStrategy(BaseStrategy):
    """MACD crossover with EMA trend filter."""

    name = "macd_ema"

    PARAMS = {
        "fast_period": {"type": "int", "default": 12, "min": 2, "max": 50, "step": 1},
        "slow_period": {"type": "int", "default": 26, "min": 5, "max": 200, "step": 1},
        "signal_period": {"type": "int", "default": 9, "min": 2, "max": 50, "step": 1},
        "ema_trend_period": {"type": "int", "default": 50, "min": 10, "max": 200, "step": 5},
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        result = macd(
            df,
            fast=self.params["fast_period"],
            slow=self.params["slow_period"],
            signal_period=self.params["signal_period"],
        )
        trend = ema(df, self.params["ema_trend_period"])

        macd_cross_up = (result.macd > result.signal) & (result.macd.shift(1) <= result.signal.shift(1))
        macd_cross_dn = (result.macd < result.signal) & (result.macd.shift(1) >= result.signal.shift(1))
        above_trend = df["close"] > trend

        signal = pd.Series(0, index=df.index, dtype=int)
        signal[macd_cross_up & above_trend] = 1
        signal[macd_cross_dn] = -1
        return signal

    def thinkscript_body(self) -> str:
        p = self.params
        return f"""\
# MACD + EMA Crossover Strategy
input fast_period = {p['fast_period']};
input slow_period = {p['slow_period']};
input signal_period = {p['signal_period']};
input ema_trend_period = {p['ema_trend_period']};

def fastMA = ExpAverage(close, fast_period);
def slowMA = ExpAverage(close, slow_period);
def macdLine = fastMA - slowMA;
def signalLine = ExpAverage(macdLine, signal_period);
def trend = ExpAverage(close, ema_trend_period);

def crossUp = macdLine crosses above signalLine;
def crossDn = macdLine crosses below signalLine;
def aboveTrend = close > trend;

def entrySignal = crossUp and aboveTrend;
def exitSignal = crossDn;

Alert(entrySignal, "MACD Entry", Alert.BAR, Sound.Chime);
Alert(exitSignal, "MACD Exit", Alert.BAR, Sound.Ring);
AddChartBubble(entrySignal, low, "▲", Color.GREEN, no);
AddChartBubble(exitSignal, high, "▼", Color.RED, yes);
plot EMALine = trend;
EMALine.SetDefaultColor(Color.CYAN);
plot MACDHist = macdLine - signalLine;
MACDHist.SetPaintingStrategy(PaintingStrategy.HISTOGRAM);
MACDHist.AssignValueColor(if MACDHist >= 0 then Color.GREEN else Color.RED);
"""
