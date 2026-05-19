from __future__ import annotations

import json
from datetime import datetime
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
    """Run a single backtest. Returns (vbt.Portfolio, BacktestMetrics).

    Automatically evaluates backtest quality using the Backtest-Expert scorer.
    """
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

    # Derive years from bar count
    if len(df) >= 2:
        delta = df.index[-1] - df.index[0]
        years = max(0.1, delta.days / 365.25)
    else:
        years = 1.0

    num_params = len(strat.PARAMS)
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
    signals: pd.Series,
    output_dir: Path | None = None,
) -> Path:
    """Export entry signals as JSON for the signal-postmortem recorder."""
    output_dir = output_dir or Path("reports/signals")
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = signals[signals == 1]
    records = []
    for ts in entries.index:
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
) -> pd.DataFrame:
    """Parameter sweep — returns a DataFrame sorted by win_rate descending."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    rows = []

    for combo in product(*values):
        params = dict(zip(keys, combo))
        try:
            _, m = run(strategy_name, df, params=params)
            row = {**params, **m.summary(), "_win_rate": m.win_rate, "_verdict": m.verdict}
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"[sweep] Skipping {params}: {exc}")

    results = pd.DataFrame(rows)
    if not results.empty:
        results = results.sort_values("_win_rate", ascending=False).drop(columns=["_win_rate"])
    return results
