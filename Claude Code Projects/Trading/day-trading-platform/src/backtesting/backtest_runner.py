from __future__ import annotations

import json
from datetime import datetime
from itertools import product
from pathlib import Path

import pandas as pd
import vectorbt as vbt
import yaml

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.backtesting.trade_rules import TRADING_MODES, enforce_trade_limits
from src.strategies.base_strategy import BaseStrategy
from src.strategies.registry import registry
from src.strategies.trailing_stop import apply_trailing_stop

_SETTINGS = Path(__file__).parents[2] / "config" / "settings.yaml"

POSITION_FRACTION = 1 / 3  # Each trade uses 1/3 of portfolio


def _load_settings() -> dict:
    with open(_SETTINGS) as f:
        return yaml.safe_load(f)


def build_signals(
    df: pd.DataFrame,
    entry_strategy: BaseStrategy,
    exit_strategy: BaseStrategy,
    stop_pct: float,
    trading_mode: str = "Day Trade",
    trailing_stop_only: bool = False,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Combine entry strategy, exit strategy, and trailing stop into filtered signals.

    trailing_stop_only: when True the exit strategy's signals are suppressed —
    only the trailing stop and EOD auto-close can exit the position.

    Returns (entries, exits, exit_reasons).
    exit_reasons is a Series with "Strategy Stop", "Trailing Stop", or "End of Day"
    at each exit bar, and "" everywhere else.
    """
    raw_entries = entry_strategy.generate_entries(df)

    if trailing_stop_only:
        raw_strategy_exits = pd.Series(0, index=df.index, dtype=int)
    else:
        raw_strategy_exits = exit_strategy.generate_exits(df)

    raw_trailing_exits = pd.Series(0, index=df.index, dtype=int)
    if stop_pct > 0:
        raw_trailing_exits = apply_trailing_stop(df, raw_entries, stop_pct)

    return enforce_trade_limits(df, raw_entries, raw_strategy_exits, raw_trailing_exits)


def run(
    entry_strategy: BaseStrategy | str,
    df: pd.DataFrame,
    exit_strategy: BaseStrategy | str | None = None,
    stop_pct: float = 0.005,
    trading_mode: str = "Day Trade",
    params: dict | None = None,
    trailing_stop_only: bool = False,
) -> tuple[object, BacktestMetrics]:
    """Run a single backtest. Returns (vbt.Portfolio, BacktestMetrics)."""
    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    cash = bt_cfg.get("initial_cash", 100_000)
    commission = bt_cfg.get("commission", 0.001)

    if isinstance(entry_strategy, str):
        entry_strategy = registry.build(entry_strategy, params=params)
    if exit_strategy is None:
        exit_strategy = entry_strategy
    elif isinstance(exit_strategy, str):
        exit_strategy = registry.build(exit_strategy)

    mode_cfg = TRADING_MODES["Day Trade"]
    freq = mode_cfg["freq"]

    entries, exits, _ = build_signals(df, entry_strategy, exit_strategy, stop_pct, trading_mode, trailing_stop_only)

    portfolio = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries.astype(bool),
        exits=exits.astype(bool),
        init_cash=cash,
        fees=commission,
        size=POSITION_FRACTION,
        size_type="percent",
        freq=freq,
    )

    if len(df) >= 2:
        delta = df.index[-1] - df.index[0]
        years = max(0.1, delta.days / 365.25)
    else:
        years = 1.0

    num_params = len(entry_strategy.PARAMS) + len(exit_strategy.PARAMS)
    metrics = compute_metrics(
        portfolio,
        years_tested=years,
        num_parameters=num_params,
        commission=commission,
    )
    return portfolio, metrics


def export_signals_for_postmortem(
    strategy_name: str,
    df: pd.DataFrame,
    entries: pd.Series,
    output_dir: Path | None = None,
) -> Path:
    """Export entry signals as JSON for the signal-postmortem recorder."""
    output_dir = output_dir or Path("reports/signals")
    output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for ts in entries.index[entries == 1]:
        price = float(df.loc[ts, "close"])
        records.append(
            {
                "signal_id": f"sig_{strategy_name}_{ts.strftime('%Y%m%d%H%M')}",
                "ticker": "",
                "signal_date": ts.strftime("%Y-%m-%d"),
                "predicted_direction": "LONG",
                "source_skill": strategy_name,
                "entry_price": price,
                "regime": "UNKNOWN",
            }
        )

    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"signals_{strategy_name}_{ts_str}.json"
    path.write_text(json.dumps({"signals": records}, indent=2), encoding="utf-8")
    return path


def sweep(
    strategy_name: str,
    df: pd.DataFrame,
    param_grid: dict[str, list],
    trading_mode: str = "Day Trade",
    stop_pct: float = 0.005,
) -> pd.DataFrame:
    """Parameter sweep — returns a DataFrame sorted by win_rate descending."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    rows = []

    for combo in product(*values):
        params = dict(zip(keys, combo))
        try:
            _, m = run(strategy_name, df, stop_pct=stop_pct, trading_mode=trading_mode, params=params)
            row = {**params, **m.summary(), "_win_rate": m.win_rate, "_verdict": m.verdict}
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"[sweep] Skipping {params}: {exc}")

    results = pd.DataFrame(rows)
    if not results.empty:
        results = results.sort_values("_win_rate", ascending=False).drop(columns=["_win_rate"])
    return results
