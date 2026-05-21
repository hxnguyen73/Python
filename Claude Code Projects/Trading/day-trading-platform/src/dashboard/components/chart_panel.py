from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.strategies.indicators import ema, vwap


def render_chart(df: pd.DataFrame, signals: pd.Series, strategy_name: str) -> None:
    """Render candlestick chart with indicator overlays and signal arrows."""
    if df.empty:
        st.warning("No data to display.")
        return

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
        subplot_titles=(f"{strategy_name.upper()} — Price", "Volume"),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # VWAP overlay
    try:
        vwap_line = vwap(df)
        fig.add_trace(
            go.Scatter(x=df.index, y=vwap_line, name="VWAP", line=dict(color="gold", width=1.5)),
            row=1, col=1,
        )
    except Exception:
        pass

    # EMA-20 overlay
    try:
        ema20 = ema(df, 20)
        fig.add_trace(
            go.Scatter(x=df.index, y=ema20, name="EMA 20", line=dict(color="cyan", width=1, dash="dot")),
            row=1, col=1,
        )
    except Exception:
        pass

    # Entry/exit arrows
    entry_idx = df.index[signals == 1]
    exit_idx = df.index[signals == -1]

    if len(entry_idx):
        fig.add_trace(
            go.Scatter(
                x=entry_idx,
                y=df.loc[entry_idx, "low"] * 0.998,
                mode="markers",
                marker=dict(symbol="triangle-up", color="lime", size=10),
                name="Entry",
            ),
            row=1, col=1,
        )

    if len(exit_idx):
        fig.add_trace(
            go.Scatter(
                x=exit_idx,
                y=df.loc[exit_idx, "high"] * 1.002,
                mode="markers",
                marker=dict(symbol="triangle-down", color="red", size=10),
                name="Exit",
            ),
            row=1, col=1,
        )

    # Volume bars
    colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=colors, showlegend=False),
        row=2, col=1,
    )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    # Allow Y axis to rescale when the user zooms on the X axis.
    # fixedrange=False unlocks the axis; autorange=True tells Plotly to
    # refit the visible bars rather than keeping the full-dataset extent.
    fig.update_yaxes(autorange=True, fixedrange=False, row=1, col=1)
    fig.update_yaxes(autorange=True, fixedrange=False, row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
