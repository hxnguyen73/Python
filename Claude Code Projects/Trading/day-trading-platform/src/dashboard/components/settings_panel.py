from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st
import yaml

from src.strategies.registry import registry

_SETTINGS_PATH = Path(__file__).parents[3] / "config" / "settings.yaml"

_TIMEFRAMES = ["5Min", "15Min", "30Min", "1Hour", "1Day"]
_TRADING_MODE = "Day Trade"


def _load_settings() -> dict:
    with open(_SETTINGS_PATH) as f:
        return yaml.safe_load(f)


def render_sidebar() -> dict:
    """Render sidebar controls and return the current user selection."""
    settings = _load_settings()
    bt_cfg = settings.get("backtest", {})
    dash_cfg = settings.get("dashboard", {})
    panel_cfg = dash_cfg.get("panels", {})

    st.sidebar.title("Day Trading Platform")

    # ── Symbols ────────────────────────────────────────────────────────────
    st.sidebar.subheader("Symbol")
    raw_symbols = st.sidebar.text_input(
        "Ticker(s) — comma-separated",
        value=dash_cfg.get("default_symbols", "AAPL"),
        help="Example: AAPL, TSLA, NVDA",
    )
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
    if not symbols:
        symbols = ["AAPL"]

    if len(symbols) > 1:
        display_symbol = st.sidebar.selectbox("Display Symbol", options=symbols)
    else:
        display_symbol = symbols[0]

    # ── Chart Timeframe ────────────────────────────────────────────────────
    st.sidebar.subheader("Chart Timeframe")
    timeframe = st.sidebar.radio(
        "Bars per candle",
        options=_TIMEFRAMES,
        index=0,
        horizontal=True,
    )

    # ── Entry / Exit Strategies ────────────────────────────────────────────
    st.sidebar.subheader("Strategies")
    strategy_names = registry.list()

    default_entry = dash_cfg.get("default_entry_strategy", "vwap")
    default_exit = dash_cfg.get("default_exit_strategy", "macd_ema")
    entry_idx = strategy_names.index(default_entry) if default_entry in strategy_names else 0
    exit_idx = strategy_names.index(default_exit) if default_exit in strategy_names else 1

    entry_strategy = st.sidebar.selectbox("Entry Strategy", options=strategy_names, index=entry_idx)
    exit_strategy = st.sidebar.selectbox("Exit Strategy", options=strategy_names, index=exit_idx)

    stop_pct = st.sidebar.number_input(
        "Trailing Stop %",
        value=dash_cfg.get("default_stop_pct", 0.5) / 100,
        step=0.001,
        min_value=0.0,
        max_value=0.20,
        format="%.3f",
        help="Trailing stop as a fraction (e.g. 0.005 = 0.5%). Set 0 to disable.",
    )
    trailing_stop_only = st.sidebar.checkbox(
        "Trailing stop as sole exit",
        value=False,
        help="When checked, ignore the exit strategy's signals — only the trailing stop or EOD close the position.",
    )

    # ── Date Range ─────────────────────────────────────────────────────────
    st.sidebar.subheader("Date Range")
    start_date = st.sidebar.date_input(
        "Start",
        value=date.fromisoformat(bt_cfg.get("default_start", "2024-01-01")),
    )
    end_date = st.sidebar.date_input(
        "End",
        value=date.fromisoformat(bt_cfg.get("default_end", "2024-12-31")),
    )

    # ── Panel visibility ───────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("Panels")
    panels = {
        "chart": st.sidebar.checkbox("Chart", value=panel_cfg.get("chart", True)),
        "signals": st.sidebar.checkbox("Signals Table", value=panel_cfg.get("signals", True)),
        "backtest": st.sidebar.checkbox("Backtest Results", value=panel_cfg.get("backtest", True)),
        "position_sizer": st.sidebar.checkbox("Position Sizer", value=panel_cfg.get("position_sizer", True)),
        "news": st.sidebar.checkbox("News", value=panel_cfg.get("news", True)),
        "strategy_editor": st.sidebar.checkbox("Strategy Editor", value=panel_cfg.get("strategy_editor", True)),
    }

    return {
        "symbols": symbols,
        "display_symbol": display_symbol,
        "trading_mode": _TRADING_MODE,
        "timeframe": timeframe,
        "entry_strategy": entry_strategy,
        "exit_strategy": exit_strategy,
        "stop_pct": stop_pct,
        "trailing_stop_only": trailing_stop_only,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "panels": panels,
    }
