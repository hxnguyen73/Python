from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import yaml

from src.strategies.registry import registry

_SETTINGS_PATH = Path(__file__).parents[3] / "config" / "settings.yaml"


def _load_settings() -> dict:
    with open(_SETTINGS_PATH) as f:
        return yaml.safe_load(f)


def render_sidebar() -> dict:
    """Render sidebar controls and return the current user selection."""
    settings = _load_settings()
    st.sidebar.title("Day Trading Platform")

    symbol = st.sidebar.selectbox(
        "Symbol",
        options=settings.get("symbols", ["AAPL"]),
        index=0,
    )

    strategy_names = registry.list()
    default_strategy = settings.get("dashboard", {}).get("default_strategy", "vwap")
    default_idx = strategy_names.index(default_strategy) if default_strategy in strategy_names else 0
    strategy = st.sidebar.selectbox("Strategy", options=strategy_names, index=default_idx)

    timeframes = settings.get("timeframes", ["1Min", "5Min", "15Min"])
    default_tf = settings.get("default_timeframe", "5Min")
    tf_idx = timeframes.index(default_tf) if default_tf in timeframes else 1
    timeframe = st.sidebar.selectbox("Timeframe", options=timeframes, index=tf_idx)

    bt_cfg = settings.get("backtest", {})
    start_date = st.sidebar.date_input(
        "Start Date",
        value=date.fromisoformat(bt_cfg.get("default_start", "2024-01-01")),
    )
    end_date = st.sidebar.date_input(
        "End Date",
        value=date.fromisoformat(bt_cfg.get("default_end", "2024-12-31")),
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Panels")
    panel_cfg = settings.get("dashboard", {}).get("panels", {})
    panels = {
        "chart": st.sidebar.checkbox("Chart", value=panel_cfg.get("chart", True)),
        "signals": st.sidebar.checkbox("Signals Table", value=panel_cfg.get("signals", True)),
        "backtest": st.sidebar.checkbox("Backtest Results", value=panel_cfg.get("backtest", True)),
        "position_sizer": st.sidebar.checkbox("Position Sizer", value=panel_cfg.get("position_sizer", True)),
        "news": st.sidebar.checkbox("News", value=panel_cfg.get("news", True)),
        "strategy_editor": st.sidebar.checkbox("Strategy Editor", value=panel_cfg.get("strategy_editor", True)),
    }

    return {
        "symbol": symbol,
        "strategy": strategy,
        "timeframe": timeframe,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "panels": panels,
    }
