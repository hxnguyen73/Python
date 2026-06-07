from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Day Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.backtesting.backtest_runner import build_signals, run as run_backtest
from src.data.data_manager import get_bars
from src.dashboard.components.backtest_panel import render_backtest
from src.dashboard.components.chart_panel import render_chart
from src.dashboard.components.news_panel import render_news
from src.dashboard.components.position_sizer_panel import render_position_sizer
from src.dashboard.components.settings_panel import render_sidebar
from src.dashboard.components.signal_panel import render_signals
from src.dashboard.components.strategy_editor import render_strategy_editor
from src.strategies.registry import registry


def _combine_signals(entries: pd.Series, exits: pd.Series) -> pd.Series:
    signals = pd.Series(0, index=entries.index, dtype=int)
    signals[entries == 1] = 1
    signals[exits == 1] = -1
    return signals


def main() -> None:
    selection = render_sidebar()

    symbol = selection["display_symbol"]
    timeframe = selection["timeframe"]          # always "5Min"
    trading_mode = selection["trading_mode"]    # always "Day Trade"
    entry_name = selection["entry_strategy"]
    exit_name = selection["exit_strategy"]
    stop_mode = selection["stop_mode"]
    stop_pct = selection["stop_pct"]
    atr_period = selection["atr_period"]
    atr_multiplier = selection["atr_multiplier"]
    trailing_stop_only = selection["trailing_stop_only"]
    start = selection["start_date"]
    end = selection["end_date"]
    panels = selection["panels"]

    st.title(f"📈 {symbol} — {entry_name.upper()} entry / {exit_name.upper()} exit")

    # Strategy editor for the entry strategy
    live_params: dict = {}
    if panels.get("strategy_editor"):
        with st.expander("Entry Strategy Parameters", expanded=False):
            live_params = render_strategy_editor(entry_name)

    # Fetch data (cached in session_state)
    cache_key = f"df_{symbol}_{timeframe}_{start}_{end}"
    if cache_key not in st.session_state:
        with st.spinner(f"Fetching {symbol} data…"):
            try:
                df = get_bars(symbol, start, end, timeframe=timeframe)
                st.session_state[cache_key] = df
            except Exception as exc:
                st.error(f"Failed to fetch data: {exc}")
                return
    else:
        df = st.session_state[cache_key]

    if df.empty:
        st.warning("No data returned for the selected symbol and date range.")
        return

    # Build strategy objects
    entry_strat = registry.build(entry_name, params=live_params or None)
    exit_strat = registry.build(exit_name)

    # Compute filtered signals + exit reasons
    entries, exits, exit_reasons = build_signals(
        df, entry_strat, exit_strat, stop_pct, trading_mode,
        trailing_stop_only, stop_mode, atr_period, atr_multiplier,
    )
    signals = _combine_signals(entries, exits)

    # Chart panel
    if panels.get("chart"):
        render_chart(df, signals, f"{entry_name}/{exit_name}")

    # Signals table with exit reasons
    if panels.get("signals"):
        render_signals(df, signals, symbol, exit_reasons=exit_reasons)

    # Backtest + quality evaluation panel
    portfolio, metrics = None, None
    if panels.get("backtest"):
        bt_key = f"bt_{symbol}_{entry_name}_{exit_name}_{stop_mode}_{stop_pct}_{atr_period}_{atr_multiplier}_{trailing_stop_only}_{trading_mode}_{timeframe}_{start}_{end}"
        if bt_key not in st.session_state or live_params:
            with st.spinner("Running backtest…"):
                try:
                    portfolio, metrics = run_backtest(
                        entry_strat,
                        df,
                        exit_strategy=exit_strat,
                        stop_pct=stop_pct,
                        trading_mode=trading_mode,
                        trailing_stop_only=trailing_stop_only,
                        stop_mode=stop_mode,
                        atr_period=atr_period,
                        atr_multiplier=atr_multiplier,
                    )
                    st.session_state[bt_key] = (portfolio, metrics)
                except Exception as exc:
                    st.error(f"Backtest failed: {exc}")
        else:
            portfolio, metrics = st.session_state[bt_key]

        if portfolio is not None and metrics is not None:
            render_backtest(portfolio, metrics)

    # Position sizer panel
    if panels.get("position_sizer"):
        with st.expander("Position Sizer", expanded=False):
            render_position_sizer(metrics)

    # News panel
    if panels.get("news"):
        render_news(symbol)


if __name__ == "__main__":
    main()
