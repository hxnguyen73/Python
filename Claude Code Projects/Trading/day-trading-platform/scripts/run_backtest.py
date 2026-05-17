"""CLI entry point for running backtests and exporting ThinkScript.

Usage:
    python scripts/run_backtest.py --strategy vwap
    python scripts/run_backtest.py --strategy rsi --start 2024-01-01 --end 2024-06-30
    python scripts/run_backtest.py --strategy orb --sweep
    python scripts/run_backtest.py --strategy macd_ema --export-thinkscript
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import yaml

from src.backtesting.backtest_runner import run, sweep
from src.data.data_manager import get_bars
from src.strategies.registry import registry


def _load_settings() -> dict:
    p = Path(__file__).parents[1] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Day Trading Platform — Backtest Runner")
    parser.add_argument("--strategy", required=True, help="Strategy name (e.g. vwap, rsi, macd_ema, orb)")
    parser.add_argument("--symbol", default=None, help="Ticker symbol (default: from settings.yaml)")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--timeframe", default=None, help="Bar timeframe (e.g. 1Min, 5Min)")
    parser.add_argument("--sweep", action="store_true", help="Run a parameter sweep (win-rate optimized)")
    parser.add_argument("--export-thinkscript", action="store_true", help="Export ThinkScript alert file")
    args = parser.parse_args()

    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    symbol = args.symbol or settings.get("default_symbol", "AAPL")
    start = args.start or bt_cfg.get("default_start", "2024-01-01")
    end = args.end or bt_cfg.get("default_end", "2024-12-31")
    timeframe = args.timeframe or settings.get("default_timeframe", "5Min")

    print(f"\n{'='*60}")
    print(f"  Strategy : {args.strategy}")
    print(f"  Symbol   : {symbol}")
    print(f"  Range    : {start} → {end}")
    print(f"  Timeframe: {timeframe}")
    print(f"{'='*60}\n")

    print("Fetching data…")
    df = get_bars(symbol, start, end, timeframe=timeframe)
    if df.empty:
        print("ERROR: No data returned. Check your .env keys and date range.")
        sys.exit(1)
    print(f"  {len(df):,} bars loaded.\n")

    if args.export_thinkscript:
        from src.alerts.thinkscript_exporter import export
        path = export(args.strategy)
        print(f"ThinkScript exported → {path}\n")

    if args.sweep:
        cls = registry.get(args.strategy)
        param_grid = {
            k: _sweep_values(v)
            for k, v in cls.PARAMS.items()
            if v["type"] in ("int", "float")
        }
        print("Running parameter sweep (sorted by Win Rate)…")
        results = sweep(args.strategy, df, param_grid)
        print(results.to_string(index=False))
    else:
        strat = registry.build(args.strategy)
        _, metrics = run(strat, df)
        print("Backtest Results")
        print("-" * 40)
        for k, v in metrics.summary().items():
            print(f"  {k:<20} {v}")
        print()


def _sweep_values(spec: dict) -> list:
    """Generate 3 evenly-spaced test values for a numeric parameter."""
    lo = spec.get("min", spec["default"] * 0.5)
    hi = spec.get("max", spec["default"] * 1.5)
    mid = (lo + hi) / 2
    if spec["type"] == "int":
        return sorted({int(lo), int(mid), int(hi)})
    return [round(v, 4) for v in (lo, mid, hi)]


if __name__ == "__main__":
    main()
