from __future__ import annotations

import streamlit as st

from src.backtesting.position_sizer import SizingParameters, calculate_position, generate_markdown_report
from src.backtesting.metrics import BacktestMetrics


def render_position_sizer(metrics: BacktestMetrics | None = None) -> None:
    """Interactive position sizing panel powered by the Position Sizer skill.

    Pre-fills Kelly inputs from backtest metrics when available.
    """
    st.subheader("Position Sizer")

    account_size = st.number_input("Account Size ($)", value=100_000.0, step=1_000.0, min_value=1.0)

    mode = st.radio("Sizing Mode", ["Fixed Fractional (Stop-Loss)", "ATR-Based", "Kelly Criterion"], horizontal=True)

    entry = stop = risk_pct = atr = atr_mult = win_rate = avg_win = avg_loss = None
    max_pos_pct = max_sector_pct = None

    if mode == "Fixed Fractional (Stop-Loss)":
        col1, col2, col3 = st.columns(3)
        entry = col1.number_input("Entry Price ($)", value=150.0, step=0.01, min_value=0.01)
        stop = col2.number_input("Stop Price ($)", value=145.0, step=0.01, min_value=0.01)
        risk_pct = col3.number_input("Risk % per Trade", value=1.0, step=0.1, min_value=0.01, max_value=10.0)

    elif mode == "ATR-Based":
        col1, col2, col3, col4 = st.columns(4)
        entry = col1.number_input("Entry Price ($)", value=150.0, step=0.01, min_value=0.01)
        atr = col2.number_input("ATR ($)", value=3.0, step=0.01, min_value=0.01)
        atr_mult = col3.number_input("ATR Multiplier", value=2.0, step=0.1, min_value=0.1)
        risk_pct = col4.number_input("Risk % per Trade", value=1.0, step=0.1, min_value=0.01, max_value=10.0)

    else:  # Kelly
        # Pre-fill from backtest metrics if available
        default_wr = round(metrics.win_rate, 4) if metrics else 0.55
        default_win = abs(metrics.avg_win) if metrics else 200.0
        default_loss = abs(metrics.avg_loss) if metrics else 100.0

        col1, col2, col3 = st.columns(3)
        win_rate = col1.number_input(
            "Win Rate (0-1)",
            value=default_wr,
            step=0.01,
            min_value=0.01,
            max_value=1.0,
            help="Auto-filled from backtest" if metrics else "",
        )
        avg_win = col2.number_input(
            "Avg Win ($)",
            value=default_win,
            step=1.0,
            min_value=0.01,
            help="Auto-filled from backtest" if metrics else "",
        )
        avg_loss = col3.number_input(
            "Avg Loss ($)",
            value=default_loss,
            step=1.0,
            min_value=0.01,
            help="Auto-filled from backtest" if metrics else "",
        )

        entry_col, stop_col = st.columns(2)
        entry_raw = entry_col.number_input("Entry Price ($, optional)", value=0.0, step=0.01, min_value=0.0)
        stop_raw = stop_col.number_input("Stop Price ($, optional)", value=0.0, step=0.01, min_value=0.0)
        entry = entry_raw if entry_raw > 0 else None
        stop = stop_raw if stop_raw > 0 else None

    with st.expander("Portfolio Constraints (optional)"):
        c1, c2 = st.columns(2)
        max_pos_raw = c1.number_input("Max Position % of Account", value=0.0, step=1.0, min_value=0.0)
        max_sector_raw = c2.number_input("Max Sector % of Account", value=0.0, step=1.0, min_value=0.0)
        max_pos_pct = max_pos_raw if max_pos_raw > 0 else None
        max_sector_pct = max_sector_raw if max_sector_raw > 0 else None
        cur_sector = c1.number_input("Current Sector Exposure %", value=0.0, step=1.0, min_value=0.0)

    if st.button("Calculate Position Size", type="primary"):
        try:
            params = SizingParameters(
                account_size=account_size,
                entry_price=entry,
                stop_price=stop,
                risk_pct=risk_pct,
                atr=atr,
                atr_multiplier=atr_mult if atr_mult else 2.0,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                max_position_pct=max_pos_pct,
                max_sector_pct=max_sector_pct,
                current_sector_exposure=cur_sector,
            )
            result = calculate_position(params)
            _render_result(result)
        except ValueError as exc:
            st.error(f"Input error: {exc}")
        except Exception as exc:
            st.error(f"Calculation failed: {exc}")


def _render_result(result: dict) -> None:
    st.markdown("---")
    if result["mode"] == "budget":
        kelly = result["calculations"]["kelly"]
        col1, col2 = st.columns(2)
        col1.metric("Full Kelly", f"{kelly['kelly_pct']:.1f}%")
        col2.metric("Half Kelly (recommended)", f"{kelly['half_kelly_pct']:.1f}%")
        st.metric(
            "Recommended Risk Budget",
            f"${result['recommended_risk_budget']:,.0f}",
            delta=f"{result['recommended_risk_budget_pct']:.1f}% of account",
        )
        st.info("Provide Entry and Stop prices to calculate exact share count.")
    else:
        shares = result["final_recommended_shares"]
        position_val = result["final_position_value"]
        risk_dollars = result.get("final_risk_dollars")
        risk_pct_val = result.get("final_risk_pct")
        binding = result.get("binding_constraint")

        col1, col2, col3 = st.columns(3)
        col1.metric("Shares", f"{shares:,}")
        col2.metric("Position Value", f"${position_val:,.0f}")
        if risk_dollars is not None:
            col3.metric("Risk", f"${risk_dollars:,.0f} ({risk_pct_val:.2f}%)")

        if binding:
            st.warning(f"Binding constraint: {binding}")

        # Show all calculation methods used
        for method, calc in result.get("calculations", {}).items():
            if calc:
                st.caption(
                    f"**{method.replace('_', ' ').title()}**: {calc.get('shares', 'N/A')} shares"
                )
