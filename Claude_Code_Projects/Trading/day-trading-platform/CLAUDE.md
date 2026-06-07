# CLAUDE.md — Day Trading Platform (V1)

## Project Purpose

Python-based day trading platform for testing intraday strategies. V1 focuses on backtesting, signal visualization, and ThinkorSwim alert export. Automated Alpaca order execution is deferred to V2.

**Primary goal:** Maximize win rate (percentage of profitable trades), not maximum profit. All strategy selection and parameter tuning must optimize for win rate first, then risk-adjusted return.

**V1 scope:**
- Fetch historical and live market data via Alpaca (data only — no order submission)
- Run backtests via VectorBT with win-rate-first reporting
- Display a customizable Streamlit dashboard with charts, indicators, and signals
- Export any strategy as paste-ready ThinkorSwim ThinkScript alerts
- Support user-defined custom strategies via a plugin registry

**Out of scope for V1:** Alpaca order submission, paper trading, live auto-execution.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Dashboard | Streamlit |
| Backtesting | VectorBT |
| Market data | Alpaca Markets API (data only) |
| TOS export | Custom ThinkScript generator |
| Config & secrets | python-dotenv + `.env` (never committed) |
| Dependency management | `requirements.txt` + `venv` |

---

## Project Structure

```
day-trading-platform/
├── .env                              # Secrets — NEVER commit (gitignored)
├── .env.example                      # Safe placeholder template (committed)
├── .gitignore
├── CLAUDE.md
├── requirements.txt
│
├── config/
│   ├── settings.yaml                 # Symbols, timeframes, data cache settings
│   └── strategies.yaml               # Parameter overrides for built-in and custom strategies
│
├── src/
│   ├── data/
│   │   ├── alpaca_client.py          # Alpaca REST wrapper — bar fetching only, no orders
│   │   └── data_manager.py           # Fetch, cache, and normalize OHLCV data
│   │
│   ├── strategies/
│   │   ├── base_strategy.py          # Abstract base class all strategies must subclass
│   │   ├── registry.py               # Auto-discovers and registers all strategy classes
│   │   ├── indicators.py             # Shared indicator functions (VWAP, EMA, MACD, RSI, ATR)
│   │   ├── vwap_strategy.py          # Built-in: VWAP reversion and breakout
│   │   ├── macd_ema_strategy.py      # Built-in: MACD crossover with EMA trend filter
│   │   ├── orb_strategy.py           # Built-in: Opening Range Breakout
│   │   ├── rsi_strategy.py           # Built-in: RSI oversold/overbought mean reversion
│   │   └── user_strategies/          # Drop-in folder for custom user-defined strategies
│   │       └── README.md             # Instructions for writing a custom strategy
│   │
│   ├── backtesting/
│   │   ├── backtest_runner.py        # VectorBT portfolio runner and parameter sweep
│   │   └── metrics.py                # Win rate, expectancy, drawdown, Sharpe
│   │
│   ├── alerts/
│   │   ├── alert_manager.py          # Real-time signal detection, desktop/sound alerts
│   │   └── thinkscript_exporter.py   # Converts any strategy to ThinkScript code
│   │
│   └── dashboard/
│       ├── app.py                    # Streamlit entry point
│       └── components/
│           ├── chart_panel.py        # Candlestick + indicator overlays (Plotly)
│           ├── signal_panel.py       # Entry/exit signal markers on chart
│           ├── backtest_panel.py     # Backtest results, equity curve, win-rate stats
│           ├── news_panel.py         # Recent news headlines via Alpaca News API
│           ├── strategy_editor.py    # Dynamic parameter controls for active strategy
│           └── settings_panel.py     # Sidebar: symbol, strategy, timeframe selectors
│
├── exports/
│   └── thinkscript/                  # Generated .ts files go here
│
├── tests/
│   ├── test_strategies.py
│   ├── test_registry.py
│   ├── test_backtesting.py
│   └── test_data_manager.py
│
└── scripts/
    ├── run_dashboard.py              # Launch: streamlit run scripts/run_dashboard.py
    └── run_backtest.py               # CLI: python scripts/run_backtest.py --strategy vwap
```

---

## Security — Mandatory Rules

**Never hardcode credentials in any `.py`, `.yaml`, or `.md` file.**

All secrets live in `.env` only — Alpaca keys are used for data fetching only in V1:

```
# .env (gitignored — never commit this file)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

Load in code with:
```python
from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv("ALPACA_API_KEY")
```

`.env.example` contains placeholder values and IS committed to git:
```
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
```

**Pre-commit:** Run `detect-secrets scan` before every commit. Block any file containing real keys or absolute paths with usernames.

---

## Customizable Strategy System

The strategy system is built around a plugin registry so users can add, modify, and tune strategies without touching core code.

### How It Works

**1. BaseStrategy contract** (`src/strategies/base_strategy.py`)

Every strategy must subclass `BaseStrategy` and implement two things:

```python
class BaseStrategy(ABC):
    # Declare parameters with type, default, and valid range for UI rendering
    PARAMS: dict[str, dict] = {}
    # Example:
    # PARAMS = {
    #     "rsi_period": {"type": "int", "default": 14, "min": 2, "max": 50, "step": 1},
    #     "oversold":   {"type": "float", "default": 30.0, "min": 10.0, "max": 45.0},
    # }

    def __init__(self, params: dict | None = None):
        # Merge PARAMS defaults with any overrides passed in or from strategies.yaml
        ...

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # Returns a Series aligned to df.index: 1=entry, -1=exit, 0=hold
        ...

    def thinkscript_body(self) -> str:
        # Override to provide a custom ThinkScript implementation.
        # Default: generic arrow-on-signal template.
        return ""
```

**2. Strategy registry** (`src/strategies/registry.py`)

On startup the registry scans two locations and auto-registers every `BaseStrategy` subclass it finds:
- `src/strategies/*.py` (built-ins)
- `src/strategies/user_strategies/*.py` (custom user strategies)

```python
# Usage
from src.strategies.registry import registry

all_names = registry.list()           # ["vwap", "macd_ema", "orb", "rsi", "my_custom"]
cls = registry.get("vwap")            # Returns VWAPStrategy class
strat = registry.build("vwap", params={"vwap_buffer_pct": 0.002})
```

No imports to update, no registration calls — just drop a file in `user_strategies/` and restart.

**3. YAML parameter overrides** (`config/strategies.yaml`)

Defaults live in each strategy's `PARAMS`. User overrides go in `strategies.yaml`:

```yaml
# config/strategies.yaml
vwap:
  vwap_buffer_pct: 0.001
  volume_multiplier: 1.8

my_custom_strategy:
  fast_period: 5
  slow_period: 20
```

The registry merges `PARAMS` defaults → `strategies.yaml` → any runtime params passed in, in that order.

**4. Dashboard strategy editor** (`src/dashboard/components/strategy_editor.py`)

When the user selects a strategy in the sidebar, `strategy_editor.py` reads that strategy's `PARAMS` definition and renders appropriate Streamlit controls:
- `"type": "int"` → `st.slider()` with min/max/step
- `"type": "float"` → `st.number_input()` with step
- `"type": "bool"` → `st.toggle()`
- `"type": "select"` with an `"options"` list → `st.selectbox()`

Changes are applied immediately to the live signal chart and can be saved back to `strategies.yaml` via a "Save Parameters" button.

**5. Adding a custom strategy**

Drop a `.py` file in `src/strategies/user_strategies/`. Minimal template:

```python
from src.strategies.base_strategy import BaseStrategy
import pandas as pd

class MyCustomStrategy(BaseStrategy):
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

Restart the dashboard — `MyCustomStrategy` appears automatically in the strategy dropdown.

---

## Built-In Strategies

All built-ins follow the `BaseStrategy` contract. Win rate is the primary optimization target.

### 1. VWAP Reversion/Breakout (`vwap_strategy.py`)
- **Entry:** Price crosses above VWAP after dipping below it, with volume spike
- **Exit:** Price crosses back below VWAP or hits `stop_pct` below entry
- **PARAMS:** `vwap_buffer_pct`, `volume_multiplier`, `stop_pct`
- **ThinkScript:** VWAP band, entry/exit bubbles on crossover

### 2. MACD + EMA Crossover (`macd_ema_strategy.py`)
- **Entry:** MACD crosses above signal line while price is above EMA (trend filter)
- **Exit:** MACD crosses below signal line
- **PARAMS:** `fast_period`, `slow_period`, `signal_period`, `ema_trend_period`
- **ThinkScript:** MACD histogram, EMA overlay, cross arrows

### 3. Opening Range Breakout (`orb_strategy.py`)
- **Setup:** High/low of first N minutes after open (5, 15, or 30 — configurable)
- **Entry:** Price breaks above range high with volume confirmation
- **Exit:** Price closes back inside range or hits stop at range low
- **PARAMS:** `range_minutes`, `volume_multiplier`, `stop_buffer_pct`
- **ThinkScript:** Horizontal range lines, breakout arrow, stop level line

### 4. RSI Oversold/Overbought (`rsi_strategy.py`)
- **Entry:** RSI crosses above `oversold_level` (default 30) with bullish confirmation candle
- **Exit:** RSI hits `overbought_level` (default 70) or reversal candle
- **PARAMS:** `rsi_period`, `oversold_level`, `overbought_level`, `confirm_bars`
- **ThinkScript:** RSI subplot, threshold lines, signal arrows

---

## Backtesting Conventions

Run via VectorBT using `vectorbt.Portfolio.from_signals()` with vectorized signal arrays.

Always report metrics in this order:
1. **Win rate** (primary) — % of closed trades that are profitable
2. Total trades
3. Expectancy (avg_win × win_rate − avg_loss × loss_rate)
4. Max drawdown
5. Sharpe ratio

Parameter optimization (`run_backtest.py --sweep`) must sweep for **highest win rate**, not highest total return or Sharpe.

Minimum backtest data: 6 months of 1-minute bars per run. Fetch via `data_manager.py`.

---

## Dashboard

Launch: `streamlit run scripts/run_dashboard.py`

**Panels (MVP):**

| Panel | File | Description |
|---|---|---|
| Chart | `chart_panel.py` | Candlestick + indicator overlays + entry/exit signal arrows |
| Volume | (subplot in chart) | Volume bars colored green/red by candle direction |
| Signals | `signal_panel.py` | Scrollable table of recent signals with timestamp and price |
| Backtest | `backtest_panel.py` | Equity curve, win rate, drawdown, expectancy |
| News | `news_panel.py` | Recent headlines from Alpaca News API |
| Strategy Editor | `strategy_editor.py` | Dynamic sliders/inputs for active strategy parameters |
| Sidebar | `settings_panel.py` | Symbol picker, strategy dropdown, timeframe selector, date range |

All chart components use Plotly via `st.plotly_chart(use_container_width=True)`. Panels are modular — each is a standalone function called from `app.py`.

The dashboard is **layout-customizable**: users can toggle panels on/off via sidebar checkboxes. Panel visibility state persists in `st.session_state`.

---

## ThinkorSwim ThinkScript Export

`thinkscript_exporter.py` generates a paste-ready `.ts` file for any registered strategy.

Output includes:
- Indicator plots (VWAP, EMA, MACD, RSI — whichever the strategy uses)
- `Alert()` calls triggered on entry and exit signal conditions
- `AddChartBubble()` for visual entry (▲) and exit (▼) markers on the price chart
- `AddCloud()` for VWAP band or range zone highlighting where applicable

Export path: `exports/thinkscript/<strategy_name>_<YYYYMMDD>.ts`

Paste into TOS: Studies → Edit Studies → New Study → paste code → Save.

CLI usage:
```bash
python scripts/run_backtest.py --strategy vwap --export-thinkscript
```

---

## Shared Indicators (`src/strategies/indicators.py`)

Reusable functions available to all strategies. Always use these rather than re-implementing per-strategy:

```python
from src.strategies.indicators import vwap, ema, macd, rsi, atr, volume_ratio
```

Each function takes a `pd.DataFrame` with standard OHLCV columns and returns a `pd.Series` or named tuple of Series. This keeps strategy code focused on signal logic only.

---

## Development Guidelines

- TDD: write tests in `tests/` before implementing strategy logic
- All `generate_signals()` implementations must have unit tests using synthetic OHLCV DataFrames
- No hardcoded symbols or dates in source — use `config/settings.yaml`
- Use `pathlib.Path` for all file paths
- Format with `black`, lint with `ruff`
- Commit prefix convention: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`

---

## Getting Started (for Claude)

When starting work in this project:
1. Confirm `.env` exists — never create it, the user manages secrets
2. Read `config/settings.yaml` for active symbols and `config/strategies.yaml` for parameter overrides
3. The strategy entry point is `src/strategies/base_strategy.py`; all new strategies subclass it
4. The registry at `src/strategies/registry.py` must auto-discover any new strategy file — do not require manual import updates
5. For dashboard changes, start at `src/dashboard/app.py`
6. For backtesting tasks, start at `src/backtesting/backtest_runner.py`

---

## V1 Milestones

- [ ] `alpaca_client.py` — fetch 1-min bars for a symbol and date range (no order methods)
- [ ] `data_manager.py` — cache bars to disk, normalize OHLCV columns
- [ ] `indicators.py` — VWAP, EMA, MACD, RSI, ATR, volume ratio functions
- [ ] `base_strategy.py` — abstract base with `PARAMS`, `generate_signals()`, `thinkscript_body()`
- [ ] `registry.py` — auto-discover strategy classes from built-ins and `user_strategies/`
- [ ] All 4 built-in strategy files with unit tests
- [ ] `backtest_runner.py` — VectorBT run, win-rate-first metric report
- [ ] `thinkscript_exporter.py` — generate `.ts` file for any strategy
- [ ] `dashboard/app.py` — Streamlit skeleton with chart, sidebar, and strategy editor
- [ ] `strategy_editor.py` — dynamic parameter controls from `PARAMS` definition
- [ ] All dashboard panels wired up with live data and signals
- [ ] `user_strategies/README.md` — custom strategy authoring guide

---

## V2 (Future — Out of Scope Now)

- Alpaca paper trading integration (`alpaca_trader.py`)
- Bracket order submission with stop-loss and take-profit
- Live auto-execution toggle in dashboard
- Trade log (`logs/trades.jsonl`) and P&L tracker
