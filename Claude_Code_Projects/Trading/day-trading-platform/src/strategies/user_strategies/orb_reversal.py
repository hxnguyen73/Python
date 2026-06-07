from __future__ import annotations

import pandas as pd

from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import atr as compute_atr

_ORB_MINUTES = 30  # 9:30–10:00 ET opening range


# ── Candle-pattern helpers ─────────────────────────────────────────────────────

def _hammer(o: float, h: float, l: float, c: float) -> bool:
    """Small body at the top with lower shadow >= 2× body and minimal upper shadow."""
    body_top = max(o, c)
    body_bot = min(o, c)
    body = body_top - body_bot
    if body <= 0:
        return False
    return (body_bot - l) >= 2 * body and (h - body_top) <= 0.5 * body


def _inverted_hammer(o: float, h: float, l: float, c: float) -> bool:
    """Small body at the bottom with upper shadow >= 2× body and minimal lower shadow."""
    body_top = max(o, c)
    body_bot = min(o, c)
    body = body_top - body_bot
    if body <= 0:
        return False
    return (h - body_top) >= 2 * body and (body_bot - l) <= 0.5 * body


def _bullish_engulfing(po: float, pc: float, co: float, cc: float) -> bool:
    """Previous bar bearish; current bar bullish and fully engulfs previous body."""
    return (
        pc < po          # prev bearish
        and cc > co      # curr bullish
        and co <= pc     # curr opens at or below prev close
        and cc >= po     # curr closes at or above prev open
    )


def _bearish_engulfing(po: float, pc: float, co: float, cc: float) -> bool:
    """Previous bar bullish; current bar bearish and fully engulfs previous body."""
    return (
        pc > po          # prev bullish
        and cc < co      # curr bearish
        and co >= pc     # curr opens at or above prev close
        and cc <= po     # curr closes at or below prev open
    )


# ── Strategy ───────────────────────────────────────────────────────────────────

class ORBReversalStrategy(BaseStrategy):
    """Reversal candle entry after a breakout from the 30-min opening range.

    The opening range (9:30–10:00 ET / 6:30–7:00 AM PST) establishes the high
    and low. This strategy only activates when the range is "significant" —
    its high-low span must be >= atr_multiple × ATR of the bars up to ORB end.

    Long entry  (body completely BELOW ORB low):
      hammer OR bullish engulfing candle  +  volume >= volume_multiplier × avg ORB vol

    Short entry (body completely ABOVE ORB high):
      inverted hammer OR bearish engulfing candle  +  volume >= volume_multiplier × avg ORB vol

    First qualifying candle per day fires; no further signals on the same day.

    generate_signals() convention (same as strong_trend_orb):
        +1 = long entry, -1 = short entry, 0 = no signal
    Use generate_entries()       for long-only VectorBT runs.
    Use generate_short_entries() for the short side.
    """

    name = "orb_reversal"

    PARAMS = {
        "atr_multiple": {
            "type": "float",
            "default": 1.0,
            "min": 0.8,
            "max": 1.6,
            "step": 0.1,
        },
        "volume_multiplier": {
            "type": "float",
            "default": 1.5,
            "min": 1.0,
            "max": 3.0,
            "step": 0.1,
        },
        "atr_period": {
            "type": "int",
            "default": 14,
            "min": 5,
            "max": 30,
            "step": 1,
        },
    }

    def _compute_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index, dtype=int)

        idx = df.index
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        et_index = idx.tz_convert("America/New_York")

        vol_mul = self.params["volume_multiplier"]
        atr_mul = self.params["atr_multiple"]
        atr_period = self.params["atr_period"]

        # Compute ATR once over the whole dataset (incorporates cross-day history)
        atr_series = compute_atr(df, period=atr_period)

        for date, day_df in df.groupby(df.index.normalize()):
            if day_df.empty:
                continue

            day_et = et_index[df.index.normalize() == date]

            market_open_et = day_et[0].replace(hour=9, minute=30, second=0, microsecond=0)
            orb_end_et = market_open_et + pd.Timedelta(minutes=_ORB_MINUTES)

            orb_mask = day_et < orb_end_et
            post_mask = day_et >= orb_end_et

            day_utc = day_df.index
            orb_df = day_df.loc[day_utc[orb_mask]]
            post_df = day_df.loc[day_utc[post_mask]]

            if orb_df.empty or post_df.empty:
                continue

            orb_high = orb_df["high"].max()
            orb_low = orb_df["low"].min()
            orb_range = orb_high - orb_low
            avg_orb_vol = orb_df["volume"].mean()

            # ATR filter: ORB must be wide enough to signal a meaningful breakout
            orb_atr = atr_series.loc[orb_df.index[-1]]
            if pd.isna(orb_atr) or orb_atr <= 0 or orb_range < atr_mul * orb_atr:
                continue

            # Last ORB bar serves as "previous" for the first post-ORB bar
            prev = orb_df.iloc[-1]

            for bar_idx in post_df.index:
                row = post_df.loc[bar_idx]
                o, h, l, c = row["open"], row["high"], row["low"], row["close"]
                vol_ok = row["volume"] >= vol_mul * avg_orb_vol

                body_top = max(o, c)
                body_bot = min(o, c)

                # Long reversal: body completely below ORB low
                if body_top < orb_low and vol_ok:
                    po, pc = prev["open"], prev["close"]
                    if _hammer(o, h, l, c) or _bullish_engulfing(po, pc, o, c):
                        signals.loc[bar_idx] = 1
                        break  # first signal wins — no more entries this day

                # Short reversal: body completely above ORB high
                elif body_bot > orb_high and vol_ok:
                    po, pc = prev["open"], prev["close"]
                    if _inverted_hammer(o, h, l, c) or _bearish_engulfing(po, pc, o, c):
                        signals.loc[bar_idx] = -1
                        break  # first signal wins — no more entries this day

                prev = row

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
# ORB Reversal Entry — reversal candle after breakout from the 30-min opening range
# Apply on a 5-minute chart. Opening range = 9:30-10:00 ET (6:30-7:00 AM PST).
input atr_multiple = {p['atr_multiple']};
input volume_multiplier = {p['volume_multiplier']};
input atr_period = {p['atr_period']};

# Opening range: 9:30-10:00 ET
def isORBPeriod = SecondsFromTime(0930) < 1800;
def isPostORB = !isORBPeriod;

def orbHigh = HighestAll(if isORBPeriod then high else 0);
def orbLow = LowestAll(if isORBPeriod then low else Double.POSITIVE_INFINITY);
def orbRange = orbHigh - orbLow;

# Average volume during the opening range
def orbVolumeSum = TotalSum(if isORBPeriod then volume else 0);
def orbBarCount = TotalSum(if isORBPeriod then 1 else 0);
def avgORBVolume = if orbBarCount > 0 then orbVolumeSum / orbBarCount else Double.NaN;

# ATR at the end of the ORB period (snapshot for the day)
def orbEndBar = isORBPeriod[1] and !isORBPeriod;
def atrSnap = if orbEndBar then Average(TrueRange(high, close, low), atr_period) else Double.NaN;
def atrForDay = HighestAll(atrSnap);
def atrFilterPassed = orbRange >= atr_multiple * atrForDay;

# Candle geometry
def bodyTop = Max(open, close);
def bodyBot = Min(open, close);
def bodySize = bodyTop - bodyBot;
def upperShadow = high - bodyTop;
def lowerShadow = bodyBot - low;

# Candle patterns
def isHammer = bodySize > 0
    and lowerShadow >= 2 * bodySize
    and upperShadow <= 0.5 * bodySize;

def isInvertedHammer = bodySize > 0
    and upperShadow >= 2 * bodySize
    and lowerShadow <= 0.5 * bodySize;

def isBullishEngulfing = close[1] < open[1]
    and close > open
    and open <= close[1]
    and close >= open[1];

def isBearishEngulfing = close[1] > open[1]
    and close < open
    and open >= close[1]
    and close <= open[1];

# Volume confirmation
def volOK = volume >= volume_multiplier * avgORBVolume;

# Entry signals
def longEntry = isPostORB and atrFilterPassed and volOK
    and bodyTop < orbLow
    and (isHammer or isBullishEngulfing);

def shortEntry = isPostORB and atrFilterPassed and volOK
    and bodyBot > orbHigh
    and (isInvertedHammer or isBearishEngulfing);

Alert(longEntry, "ORB Reversal Long Entry", Alert.BAR, Sound.Chime);
Alert(shortEntry, "ORB Reversal Short Entry", Alert.BAR, Sound.Bell);
AddChartBubble(longEntry, low, "\\u25b2 Rev Long", Color.CYAN, no);
AddChartBubble(shortEntry, high, "\\u25bc Rev Short", Color.MAGENTA, yes);

plot ORBHigh = orbHigh;
ORBHigh.SetDefaultColor(Color.GREEN);
ORBHigh.SetStyle(Curve.LONG_DASH);
plot ORBLow = orbLow;
ORBLow.SetDefaultColor(Color.RED);
ORBLow.SetStyle(Curve.LONG_DASH);
AddCloud(orbHigh, orbLow, Color.DARK_GREEN, Color.DARK_RED);
"""
