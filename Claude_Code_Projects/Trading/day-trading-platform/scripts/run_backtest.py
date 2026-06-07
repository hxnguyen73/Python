"""CLI entry point for running backtests, position sizing, and ThinkScript export.

Usage:
    python scripts/run_backtest.py --entry-strategy vwap
    python scripts/run_backtest.py --entry-strategy vwap --exit-strategy macd_ema
    python scripts/run_backtest.py --entry-strategy rsi --start 2024-01-01 --end 2024-06-30
    python scripts/run_backtest.py --entry-strategy orb --sweep
    python scripts/run_backtest.py --entry-strategy macd_ema --export-thinkscript
    python scripts/run_backtest.py --entry-strategy vwap --export-signals
    python scripts/run_backtest.py --entry-strategy vwap --position-sizer --entry 155 --stop 150
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import yaml

from src.backtesting.backtest_runner import build_signals, export_signals_for_postmortem, run, sweep
from src.data.data_manager import get_bars
from src.strategies.registry import registry


def _load_settings() -> dict:
    p = Path(__file__).parents[1] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Day Trading Platform — Backtest Runner")
    parser.add_argument("--entry-strategy", default=None, help="Entry strategy (vwap, rsi, macd_ema, orb)")
    parser.add_argument("--exit-strategy", default=None, help="Exit strategy (defaults to entry strategy)")
    parser.add_argument("--trading-mode", default=None, help="Day Trade | Swing Trade | Position Trade")
    parser.add_argument("--stop-pct", type=float, default=None, help="Trailing stop %% (e.g. 0.5 = 0.5%%)")
    # Legacy --strategy flag still works as --entry-strategy alias
    parser.add_argument("--strategy", default=None, help="Alias for --entry-strategy")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--sweep", action="store_true", help="Parameter sweep (win-rate optimized)")
    parser.add_argument("--export-thinkscript", action="store_true")
    parser.add_argument("--export-signals", action="store_true", help="Export entry signals JSON for postmortem")
    parser.add_argument("--position-sizer", action="store_true", help="Run position sizing after backtest")
    parser.add_argument("--entry", type=float, help="Entry price for position sizer")
    parser.add_argument("--stop", type=float, help="Stop price for position sizer")
    parser.add_argument("--risk-pct", type=float, default=1.0, help="Risk %% per trade (default 1.0)")
    parser.add_argument("--account-size", type=float, default=None, help="Account size for position sizer")
    args = parser.parse_args()

    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    dash_cfg = settings.get("dashboard", {})

    entry_name = args.entry_strategy or args.strategy or dash_cfg.get("default_entry_strategy", "vwap")
    exit_name = args.exit_strategy or dash_cfg.get("default_exit_strategy", entry_name)
    trading_mode = args.trading_mode or dash_cfg.get("default_trading_mode", "Day Trade")
    stop_pct = (args.stop_pct or dash_cfg.get("default_stop_pct", 0.5)) / 100
    symbol = args.symbol or dash_cfg.get("default_symbols", "AAPL").split(",")[0].strip()
    start = args.start or bt_cfg.get("default_start", "2024-01-01")
    end = args.end or bt_cfg.get("default_end", "2024-12-31")
    timeframe_arg = args.timeframe
    account_size = args.account_size or bt_cfg.get("initial_cash", 100_000)

    # Timeframe from trading mode if not overridden
    from src.backtesting.trade_rules import TRADING_MODES
    mode_cfg = TRADING_MODES.get(trading_mode, TRADING_MODES["Day Trade"])
    timeframe = timeframe_arg or mode_cfg["timeframe"]

    print(f"\n{'='*60}")
    print(f"  Entry    : {entry_name}")
    print(f"  Exit     : {exit_name}")
    print(f"  Mode     : {trading_mode}  ({timeframe})")
    print(f"  Stop     : {stop_pct*100:.2f}%%")
    print(f"  Symbol   : {symbol}")
    print(f"  Range    : {start} → {end}")
    print(f"{'='*60}\n")

    if args.export_thinkscript:
        from src.alerts.thinkscript_exporter import export
        path = export(entry_name)
        print(f"ThinkScript exported → {path}\n")

    print("Fetching data…")
    df = get_bars(symbol, start, end, timeframe=timeframe)
    if df.empty:
        print("ERROR: No data returned. Check your .env keys and date range.")
        sys.exit(1)
    print(f"  {len(df):,} bars loaded.\n")

    if args.sweep:
        cls = registry.get(entry_name)
        param_grid = {
            k: _sweep_values(v)
            for k, v in cls.PARAMS.items()
            if v["type"] in ("int", "float")
        }
        print("Running parameter sweep (sorted by Win Rate)…")
        results = sweep(entry_name, df, param_grid, trading_mode=trading_mode, stop_pct=stop_pct)
        if "_verdict" in results.columns:
            print(results[["Win Rate", "Total Trades", "_verdict", *list(param_grid.keys())]].to_string(index=False))
        else:
            print(results.to_string(index=False))
        return

    entry_strat = registry.build(entry_name)
    exit_strat = registry.build(exit_name)
    portfolio, metrics = run(entry_strat, df, exit_strategy=exit_strat, stop_pct=stop_pct, trading_mode=trading_mode)

    print("Backtest Results")
    print("-" * 40)
    for k, v in metrics.summary().items():
        print(f"  {k:<20} {v}")

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

    if args.export_signals:
        entries, _ = build_signals(df, entry_strat, exit_strat, stop_pct, trading_mode)
        path = export_signals_for_postmortem(entry_name, df, entries)
        print(f"\nSignals exported → {path}")

    if args.position_sizer:
        _run_position_sizer(args, metrics, account_size)

    print()


def _run_position_sizer(args, metrics, account_size: float) -> None:
    from src.backtesting.position_sizer import SizingParameters, calculate_position, generate_markdown_report

    print("\n" + "=" * 40)
    print("Position Sizer")
    print("=" * 40)

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
