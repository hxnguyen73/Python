from __future__ import annotations

import pandas as pd
import streamlit as st


def render_signals(df: pd.DataFrame, signals: pd.Series, symbol: str) -> None:
    """Render a scrollable table of recent entry/exit signals."""
    st.subheader("Recent Signals")

    active = signals[signals != 0].copy()
    if active.empty:
        st.info("No signals generated for this period.")
        return

    rows = []
    for ts in active.index:
        val = int(active.loc[ts])
        price = float(df.loc[ts, "close"])
        rows.append(
            {
                "Timestamp": ts,
                "Symbol": symbol,
                "Action": "ENTRY ▲" if val == 1 else "EXIT ▼",
                "Price": f"${price:.2f}",
                "Signal": val,
            }
        )

    tbl = pd.DataFrame(rows).sort_values("Timestamp", ascending=False).head(50)

    def _color_action(val: str) -> str:
        return "color: lime" if "ENTRY" in val else "color: red"

    styled = tbl.drop(columns=["Signal"]).style.applymap(_color_action, subset=["Action"])
    st.dataframe(styled, use_container_width=True, height=300)
