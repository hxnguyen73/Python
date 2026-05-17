from __future__ import annotations

import pandas as pd
import plotly.graph_objects as st_go
import streamlit as st

from src.backtesting.metrics import BacktestMetrics


def render_backtest(portfolio, metrics: BacktestMetrics) -> None:
    """Render equity curve, win-rate stats, and key metrics."""
    st.subheader("Backtest Results")

    # Metric tiles — win rate first per project convention
    cols = st.columns(4)
    summary = metrics.summary()
    keys = ["Win Rate", "Total Trades", "Expectancy", "Max Drawdown", "Sharpe Ratio", "Total Return"]

    for i, key in enumerate(keys[:4]):
        cols[i].metric(key, summary.get(key, "N/A"))

    cols2 = st.columns(4)
    for i, key in enumerate(keys[4:]):
        cols2[i].metric(key, summary.get(key, "N/A"))

    # Equity curve
    try:
        equity = portfolio.value()
        fig = st_go.Figure()
        fig.add_trace(
            st_go.Scatter(
                x=equity.index,
                y=equity.values,
                fill="tozeroy",
                line=dict(color="#26a69a"),
                name="Portfolio Value",
            )
        )
        fig.update_layout(
            title="Equity Curve",
            template="plotly_dark",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_title=None,
            yaxis_title="Value ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Could not render equity curve: {exc}")
