from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Day Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.backtesting.backtest_runner import run as run_backtest
from src.data.data_manager import get_bars
from src.dashboard.components.backtest_panel import render_backtest
from src.dashboard.components.chart_panel import render_chart
from src.dashboard.components.news_panel import render_news
from src.dashboard.components.position_sizer_panel import render_position_sizer
from src.dashboard.components.settings_panel import render_sidebar
from src.dashboard.components.signal_panel import render_signals
from src.dashboard.components.strategy_editor import render_strategy_editor
from src.strategies.registry import registry


def main() -> None:
    selection = render_sidebar()
    symbol = selection["symbol"]
    strategy_name = selection["strategy"]
    timeframe = selection["timeframe"]
    start = selection["start_date"]
    end = selection["end_date"]
    panels = selection["panels"]

    st.title(f"📈 {symbol} — {strategy_name.upper()}")

    # Strategy editor — runs before signal computation to pick up live params
    live_params: dict = {}
    if panels.get("strategy_editor"):
        with st.expander("Strategy Parameters", expanded=False):
            live_params = render_strategy_editor(strategy_name)

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

    # Compute signals
    strat = registry.build(strategy_name, params=live_params or None)
    signals = strat.generate_signals(df)

    # Chart panel
    if panels.get("chart"):
        render_chart(df, signals, strategy_name)

    # Signals table
    if panels.get("signals"):
        render_signals(df, signals, symbol)

    # Backtest + quality evaluation panel
    portfolio, metrics = None, None
    if panels.get("backtest"):
        bt_key = f"bt_{symbol}_{strategy_name}_{timeframe}_{start}_{end}"
        if bt_key not in st.session_state or live_params:
            with st.spinner("Running backtest…"):
                try:
                    portfolio, metrics = run_backtest(strat, df)
                    st.session_state[bt_key] = (portfolio, metrics)
                except Exception as exc:
                    st.error(f"Backtest failed: {exc}")
        else:
            portfolio, metrics = st.session_state[bt_key]

        if portfolio is not None and metrics is not None:
            render_backtest(portfolio, metrics)

    # Position sizer panel (pre-filled from backtest metrics when available)
    if panels.get("position_sizer"):
        with st.expander("Position Sizer", expanded=False):
            render_position_sizer(metrics)

    # News panel
    if panels.get("news"):
        render_news(symbol)


if __name__ == "__main__":
    main()
