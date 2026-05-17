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

    # Strategy editor (updates live params before computing signals)
    live_params: dict = {}
    if panels.get("strategy_editor"):
        with st.expander("Strategy Parameters", expanded=False):
            live_params = render_strategy_editor(strategy_name)

    # Fetch data (cached in session_state to avoid redundant network calls)
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

    # Backtest panel
    if panels.get("backtest"):
        bt_key = f"bt_{symbol}_{strategy_name}_{timeframe}_{start}_{end}"
        if bt_key not in st.session_state or live_params:
            with st.spinner("Running backtest…"):
                try:
                    portfolio, metrics = run_backtest(strat, df)
                    st.session_state[bt_key] = (portfolio, metrics)
                except Exception as exc:
                    st.error(f"Backtest failed: {exc}")
                    portfolio, metrics = None, None
        else:
            portfolio, metrics = st.session_state[bt_key]

        if portfolio is not None and metrics is not None:
            render_backtest(portfolio, metrics)

    # News panel
    if panels.get("news"):
        render_news(symbol)


if __name__ == "__main__":
    main()
