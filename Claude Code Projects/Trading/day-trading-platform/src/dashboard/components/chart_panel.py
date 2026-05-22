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

    # Convert UTC timestamps to LA local time for display only
    la_tz = "America/Los_Angeles"
    if df.index.tz is None:
        la_index = df.index.tz_localize("UTC").tz_convert(la_tz)
    else:
        la_index = df.index.tz_convert(la_tz)

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
            x=la_index,
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
            go.Scatter(x=la_index, y=vwap_line, name="VWAP", line=dict(color="gold", width=1.5)),
            row=1, col=1,
        )
    except Exception:
        pass

    # EMA-20 overlay
    try:
        ema20 = ema(df, 20)
        fig.add_trace(
            go.Scatter(x=la_index, y=ema20, name="EMA 20", line=dict(color="cyan", width=1, dash="dot")),
            row=1, col=1,
        )
    except Exception:
        pass

    # Entry/exit arrows — convert signal timestamps to LA time
    entry_utc = df.index[signals == 1]
    exit_utc = df.index[signals == -1]

    if len(entry_utc):
        entry_la = entry_utc.tz_convert(la_tz) if entry_utc.tz else entry_utc.tz_localize("UTC").tz_convert(la_tz)
        fig.add_trace(
            go.Scatter(
                x=entry_la,
                y=df.loc[entry_utc, "low"] * 0.998,
                mode="markers",
                marker=dict(symbol="triangle-up", color="lime", size=10),
                name="Entry",
            ),
            row=1, col=1,
        )

    if len(exit_utc):
        exit_la = exit_utc.tz_convert(la_tz) if exit_utc.tz else exit_utc.tz_localize("UTC").tz_convert(la_tz)
        fig.add_trace(
            go.Scatter(
                x=exit_la,
                y=df.loc[exit_utc, "high"] * 1.002,
                mode="markers",
                marker=dict(symbol="triangle-down", color="red", size=10),
                name="Exit",
            ),
            row=1, col=1,
        )

    # Volume bars
    colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=la_index, y=df["volume"], name="Volume", marker_color=colors, showlegend=False),
        row=2, col=1,
    )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    # Price axis: auto-range so zooming X rescales Y to visible bars.
    fig.update_yaxes(autorange=True, fixedrange=False, row=1, col=1)

    # Volume axis: cap at the 95th-percentile so one spike day doesn't
    # squash every other bar to a sliver. fixedrange=False keeps it interactive.
    vol_ceil = df["volume"].quantile(0.95) * 1.1
    fig.update_yaxes(range=[0, vol_ceil], fixedrange=False, row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
