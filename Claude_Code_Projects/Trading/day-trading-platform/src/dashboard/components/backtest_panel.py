from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.backtesting.metrics import BacktestMetrics

_VERDICT_COLOR = {"Deploy": "green", "Refine": "orange", "Abandon": "red"}
_SEVERITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def render_backtest(portfolio, metrics: BacktestMetrics) -> None:
    """Render equity curve, win-rate stats, and Backtest-Expert quality evaluation."""
    st.subheader("Backtest Results")

    # Primary metric tiles — win rate first per project convention
    summary = metrics.summary()
    keys = ["Win Rate", "Total Trades", "Expectancy", "Max Drawdown", "Sharpe Ratio", "Total Return"]

    cols = st.columns(4)
    for i, key in enumerate(keys[:4]):
        cols[i].metric(key, summary.get(key, "N/A"))

    cols2 = st.columns(4)
    for i, key in enumerate(keys[4:]):
        cols2[i].metric(key, summary.get(key, "N/A"))

    # Equity curve
    try:
        equity = portfolio.value()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
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
            height=280,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_title=None,
            yaxis_title="Value ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Could not render equity curve: {exc}")

    # ── Backtest-Expert quality panel ──────────────────────────────────────
    if not metrics.quality:
        return

    quality = metrics.quality
    verdict = quality.get("verdict", "N/A")
    score = quality.get("total_score", 0)
    color = _VERDICT_COLOR.get(verdict, "gray")

    st.markdown("---")
    st.subheader("Strategy Quality — Backtest Expert")

    verdict_col, score_col, _ = st.columns([1, 1, 2])
    verdict_col.metric("Verdict", verdict)
    score_col.metric("Quality Score", f"{score} / 100")

    # 5-dimension bar chart
    dims = quality.get("dimensions", [])
    if dims:
        names = [d["name"] for d in dims]
        scores = [d["score"] for d in dims]
        maxes = [d["max_score"] for d in dims]

        bar_colors = [
            "#26a69a" if s >= m * 0.7 else "#ef9a9a" if s < m * 0.4 else "#ffcc80"
            for s, m in zip(scores, maxes)
        ]

        fig2 = go.Figure(
            go.Bar(
                x=names,
                y=scores,
                marker_color=bar_colors,
                text=[f"{s}/{m}" for s, m in zip(scores, maxes)],
                textposition="outside",
            )
        )
        fig2.update_layout(
            title="5-Dimension Scores",
            template="plotly_dark",
            height=260,
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis=dict(range=[0, 22], title="Score"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Red flags
    flags = quality.get("red_flags", [])
    if flags:
        st.markdown("**Red Flags**")
        for flag in flags:
            icon = _SEVERITY_ICON.get(flag.get("severity", "low"), "⚪")
            st.markdown(f"{icon} {flag['message']}")
    else:
        st.success("No red flags detected.")

    # Profit factor + expectancy
    pf = quality.get("profit_factor")
    exp = quality.get("expectancy")
    if pf is not None and exp is not None:
        pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"
        st.caption(f"Profit Factor: **{pf_str}** | Expectancy: **{exp:.3f}%** per trade")
