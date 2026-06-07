from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import rsi


class RSIStrategy(BaseStrategy):
    """RSI oversold/overbought mean reversion."""

    name = "rsi"

    PARAMS = {
        "rsi_period": {"type": "int", "default": 14, "min": 2, "max": 50, "step": 1},
        "oversold_level": {"type": "float", "default": 30.0, "min": 10.0, "max": 45.0, "step": 1.0},
        "overbought_level": {"type": "float", "default": 70.0, "min": 55.0, "max": 90.0, "step": 1.0},
        "confirm_bars": {"type": "int", "default": 1, "min": 1, "max": 5, "step": 1},
    }

    def generate_entries(self, df: pd.DataFrame) -> pd.Series:
        rsi_line = rsi(df, self.params["rsi_period"])
        oversold = self.params["oversold_level"]
        confirm = self.params["confirm_bars"]
        was_oversold = rsi_line.shift(confirm) < oversold
        crosses_up = rsi_line > oversold
        bullish_candle = df["close"] > df["open"]
        return (was_oversold & crosses_up & bullish_candle).astype(int)

    def generate_exits(self, df: pd.DataFrame) -> pd.Series:
        rsi_line = rsi(df, self.params["rsi_period"])
        overbought = self.params["overbought_level"]
        return (rsi_line >= overbought).astype(int)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signal = pd.Series(0, index=df.index, dtype=int)
        signal[self.generate_entries(df) == 1] = 1
        signal[self.generate_exits(df) == 1] = -1
        return signal

    def thinkscript_body(self) -> str:
        p = self.params
        return f"""\
# RSI Oversold/Overbought Mean Reversion
input rsi_period = {p['rsi_period']};
input oversold_level = {p['oversold_level']};
input overbought_level = {p['overbought_level']};
input confirm_bars = {p['confirm_bars']};

def rsiValue = RSI(length = rsi_period);
def wasOversold = rsiValue[confirm_bars] < oversold_level;
def bullishCandle = close > open;

def entrySignal = wasOversold and rsiValue > oversold_level and bullishCandle;
def exitSignal = rsiValue >= overbought_level;

Alert(entrySignal, "RSI Oversold Entry", Alert.BAR, Sound.Chime);
Alert(exitSignal, "RSI Overbought Exit", Alert.BAR, Sound.Ring);
AddChartBubble(entrySignal, low, "▲", Color.GREEN, no);
AddChartBubble(exitSignal, high, "▼", Color.RED, yes);
plot RSILine = rsiValue;
plot OversoldLine = oversold_level;
OversoldLine.SetDefaultColor(Color.GREEN);
plot OverboughtLine = overbought_level;
OverboughtLine.SetDefaultColor(Color.RED);
RSILine.SetDefaultColor(Color.YELLOW);
"""
