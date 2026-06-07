# Custom Strategy Guide

Drop a `.py` file in this folder. The registry auto-discovers it on the next restart — no imports to update.

## Minimal Template

```python
from src.strategies.base_strategy import BaseStrategy
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    name = "my_custom"   # registry key shown in the dashboard dropdown

    PARAMS = {
        "fast_period": {"type": "int", "default": 9, "min": 2, "max": 50, "step": 1},
        "slow_period": {"type": "int", "default": 21, "min": 5, "max": 200, "step": 1},
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = df["close"].ewm(span=self.params["fast_period"]).mean()
        slow = df["close"].ewm(span=self.params["slow_period"]).mean()
        signal = pd.Series(0, index=df.index)
        signal[fast > slow] = 1
        signal[fast < slow] = -1
        return signal
```

## PARAMS Field Reference

| key | type value | required extras |
|---|---|---|
| `"type": "int"` | integer slider | `min`, `max`, `step` |
| `"type": "float"` | number input | `min`, `max`, `step` |
| `"type": "bool"` | toggle | — |
| `"type": "select"` | dropdown | `options: [...]` |

## generate_signals Contract

- Input: `df` with columns `open`, `high`, `low`, `close`, `volume` and a tz-aware DatetimeIndex.
- Output: `pd.Series` aligned to `df.index` where `1 = entry`, `-1 = exit`, `0 = hold`.

## Optional: ThinkScript Export

Override `thinkscript_body()` to return a ThinkScript snippet. The exporter wraps it in a study header automatically:

```python
def thinkscript_body(self) -> str:
    return "# my custom ThinkScript code here"
```

## Shared Indicators

```python
from src.strategies.indicators import vwap, ema, macd, rsi, atr, volume_ratio
```

All functions take `df` and return a `pd.Series`.
