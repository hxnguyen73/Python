"""CLI entry point for running backtests, position sizing, and ThinkScript export.

Usage:
    python scripts/run_backtest.py --strategy vwap
    python scripts/run_backtest.py --strategy rsi --start 2024-01-01 --end 2024-06-30
    python scripts/run_backtest.py --strategy orb --sweep
    python scripts/run_backtest.py --strategy macd_ema --export-thinkscript
    python scripts/run_backtest.py --strategy vwap --position-sizer --entry 155 --stop 150
    python scripts/run_backtest.py --strategy vwap --export-signals
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import yaml

from src.backtesting.backtest_runner import export_signals_for_postmortem, run, sweep
from src.backtesting.evaluate_backtest import to_markdown as quality_to_markdown
from src.data.data_manager import get_bars
from src.strategies.registry import registry


def _load_settings() -> dict:
    p = Path(__file__).parents[1] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Day Trading Platform — Backtest Runner")
    parser.add_argument("--strategy", required=True, help="Strategy name (vwap, rsi, macd_ema, orb)")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--sweep", action="store_true", help="Parameter sweep (win-rate optimized)")
    parser.add_argument("--export-thinkscript", action="store_true")
    parser.add_argument("--export-signals", action="store_true", help="Export entry signals JSON for postmortem")
    # Position sizer flags (mirrors position_sizer.py CLI)
    parser.add_argument("--position-sizer", action="store_true", help="Run position sizing after backtest")
    parser.add_argument("--entry", type=float, help="Entry price for position sizer")
    parser.add_argument("--stop", type=float, help="Stop price for position sizer")
    parser.add_argument("--risk-pct", type=float, default=1.0, help="Risk %% per trade (default 1.0)")
    parser.add_argument("--account-size", type=float, default=None, help="Account size for position sizer")
    args = parser.parse_args()

    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    symbol = args.symbol or settings.get("default_symbol", "AAPL")
    start = args.start or bt_cfg.get("default_start", "2024-01-01")
    end = args.end or bt_cfg.get("default_end", "2024-12-31")
    timeframe = args.timeframe or settings.get("default_timeframe", "5Min")
    account_size = args.account_size or bt_cfg.get("initial_cash", 100_000)

    print(f"\n{'='*60}")
    print(f"  Strategy : {args.strategy}")
    print(f"  Symbol   : {symbol}")
    print(f"  Range    : {start} → {end}")
    print(f"  Timeframe: {timeframe}")
    print(f"{'='*60}\n")

    # ThinkScript export (no data needed)
    if args.export_thinkscript:
        from src.alerts.thinkscript_exporter import export
        path = export(args.strategy)
        print(f"ThinkScript exported → {path}\n")

    print("Fetching data…")
    df = get_bars(symbol, start, end, timeframe=timeframe)
    if df.empty:
        print("ERROR: No data returned. Check your .env keys and date range.")
        sys.exit(1)
    print(f"  {len(df):,} bars loaded.\n")

    if args.sweep:
        cls = registry.get(args.strategy)
        param_grid = {
            k: _sweep_values(v)
            for k, v in cls.PARAMS.items()
            if v["type"] in ("int", "float")
        }
        print("Running parameter sweep (sorted by Win Rate)…")
        results = sweep(args.strategy, df, param_grid)
        if "_verdict" in results.columns:
            print(results[["Win Rate", "Total Trades", "_verdict", *list(param_grid.keys())]].to_string(index=False))
        else:
            print(results.to_string(index=False))
        return

    strat = registry.build(args.strategy)
    portfolio, metrics = run(strat, df)

    # Core backtest results
    print("Backtest Results")
    print("-" * 40)
    for k, v in metrics.summary().items():
        print(f"  {k:<20} {v}")

    # Quality evaluation from Backtest-Expert
    if metrics.quality:
        print(f"\nBacktest-Expert Quality: {metrics.quality_score}/100 — {metrics.verdict}")
        flags = metrics.quality.get("red_flags", [])
        if flags:
            print(f"  Red flags ({len(flags)}):")
            for f in flags:
                sev = f["severity"].upper()
                print(f"    [{sev}] {f['message']}")
        else:
            print("  No red flags.")

    # Export signals for postmortem
    if args.export_signals:
        signals = strat.generate_signals(df)
        path = export_signals_for_postmortem(args.strategy, df, signals)
        print(f"\nSignals exported → {path}")
        print(f"  Run postmortem: python -m src.backtesting.postmortem_recorder --signals-file {path}")

    # Position sizer
    if args.position_sizer:
        _run_position_sizer(args, metrics, account_size)

    print()


def _run_position_sizer(args, metrics, account_size: float) -> None:
    from src.backtesting.position_sizer import SizingParameters, calculate_position, generate_markdown_report

    print("\n" + "=" * 40)
    print("Position Sizer")
    print("=" * 40)

    # Prefer fixed-fractional if entry+stop given, else Kelly from backtest metrics
    if args.entry and args.stop:
        params = SizingParameters(
            account_size=account_size,
            entry_price=args.entry,
            stop_price=args.stop,
            risk_pct=args.risk_pct,
        )
    elif metrics.win_rate > 0:
        print("  (Using Kelly Criterion from backtest metrics)")
        params = SizingParameters(
            account_size=account_size,
            entry_price=args.entry,
            stop_price=args.stop,
            win_rate=metrics.win_rate,
            avg_win=abs(metrics.avg_win) or 1.0,
            avg_loss=abs(metrics.avg_loss) or 1.0,
        )
    else:
        print("  No entry/stop or backtest metrics available for position sizing.")
        return

    try:
        result = calculate_position(params)
        print(generate_markdown_report(result))
    except ValueError as exc:
        print(f"  Error: {exc}")


def _sweep_values(spec: dict) -> list:
    lo = spec.get("min", spec["default"] * 0.5)
    hi = spec.get("max", spec["default"] * 1.5)
    mid = (lo + hi) / 2
    if spec["type"] == "int":
        return sorted({int(lo), int(mid), int(hi)})
    return [round(v, 4) for v in (lo, mid, hi)]


if __name__ == "__main__":
    main()
