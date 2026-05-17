from __future__ import annotations

from itertools import product
from pathlib import Path

import pandas as pd
import vectorbt as vbt
import yaml

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.strategies.base_strategy import BaseStrategy
from src.strategies.registry import registry

_SETTINGS = Path(__file__).parents[2] / "config" / "settings.yaml"


def _load_settings() -> dict:
    with open(_SETTINGS) as f:
        return yaml.safe_load(f)


def run(
    strategy: BaseStrategy | str,
    df: pd.DataFrame,
    params: dict | None = None,
) -> tuple[object, BacktestMetrics]:
    """Run a single backtest. Returns (vbt.Portfolio, BacktestMetrics)."""
    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    cash = bt_cfg.get("initial_cash", 100_000)
    commission = bt_cfg.get("commission", 0.001)

    if isinstance(strategy, str):
        strat = registry.build(strategy, params=params)
    else:
        strat = strategy

    signals = strat.generate_signals(df)
    entries = signals == 1
    exits = signals == -1

    portfolio = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        init_cash=cash,
        fees=commission,
        freq="1T",
    )

    metrics = compute_metrics(portfolio)
    return portfolio, metrics


def sweep(
    strategy_name: str,
    df: pd.DataFrame,
    param_grid: dict[str, list],
) -> pd.DataFrame:
    """Parameter sweep — returns a DataFrame sorted by win_rate descending."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    rows = []

    for combo in product(*values):
        params = dict(zip(keys, combo))
        try:
            _, m = run(strategy_name, df, params=params)
            row = {**params, **m.summary(), "_win_rate": m.win_rate}
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"[sweep] Skipping {params}: {exc}")

    results = pd.DataFrame(rows)
    if not results.empty:
        results = results.sort_values("_win_rate", ascending=False).drop(columns=["_win_rate"])
    return results
