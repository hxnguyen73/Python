from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

_SETTINGS_PATH = Path(__file__).parents[3] / "config" / "settings.yaml"
_POSITION_FRACTION = 1 / 3


def _load_initial_cash() -> float:
    try:
        with open(_SETTINGS_PATH) as f:
            cfg = yaml.safe_load(f)
        return float(cfg.get("backtest", {}).get("initial_cash", 100_000))
    except Exception:
        return 100_000.0


def _pair_trades(
    signals: pd.Series,
    df: pd.DataFrame,
    initial_cash: float,
    exit_reasons: pd.Series | None,
) -> pd.DataFrame:
    """Convert entry/exit signals into one row per trade with P&L and exit reason."""
    rows: list[dict] = []
    pending: dict | None = None
    portfolio_value = initial_cash

    for ts in signals.index:
        val = int(signals.loc[ts])
        price = float(df.loc[ts, "close"])

        if val == 1:  # entry — deploy 1/3 of current portfolio
            txn_value = portfolio_value * _POSITION_FRACTION
            pending = {"Entry Time": ts, "Entry Price": price, "Txn Value": txn_value}

        elif val == -1 and pending is not None:
            entry_price = pending["Entry Price"]
            txn_value = pending["Txn Value"]
            pnl_pct = (price - entry_price) / entry_price * 100
            pnl_usd = txn_value * pnl_pct / 100
            portfolio_value += pnl_usd

            reason = ""
            if exit_reasons is not None and ts in exit_reasons.index:
                reason = str(exit_reasons.loc[ts])

            rows.append(
                {
                    "Entry Time": pending["Entry Time"],
                    "Entry $": f"${entry_price:.2f}",
                    "Exit Time": ts,
                    "Exit $": f"${price:.2f}",
                    "Exit Reason": reason,
                    "Txn Value $": f"${txn_value:,.0f}",
                    "P&L %": f"{pnl_pct:+.2f}%",
                    "P&L $": f"${pnl_usd:+,.0f}",
                    "_pnl": pnl_pct,
                }
            )
            pending = None

    # Unpaired entry — position still open
    if pending is not None:
        rows.append(
            {
                "Entry Time": pending["Entry Time"],
                "Entry $": f"${pending['Entry Price']:.2f}",
                "Exit Time": "—",
                "Exit $": "—",
                "Exit Reason": "Open",
                "Txn Value $": f"${pending['Txn Value']:,.0f}",
                "P&L %": "Open",
                "P&L $": "Open",
                "_pnl": None,
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("Entry Time", ascending=False).head(50)


def render_signals(
    df: pd.DataFrame,
    signals: pd.Series,
    symbol: str,
    exit_reasons: pd.Series | None = None,
) -> None:
    """Render a scrollable table of recent trades with P&L and exit reason."""
    st.subheader(f"Recent Signals — {symbol}")

    if signals[signals != 0].empty:
        st.info("No signals generated for this period.")
        return

    initial_cash = _load_initial_cash()
    tbl = _pair_trades(signals, df, initial_cash, exit_reasons)

    if tbl.empty:
        st.info("No completed trades to display.")
        return

    display = tbl.drop(columns=["_pnl"])

    def _color_row(row: pd.Series) -> list[str]:
        pnl_val = tbl.loc[row.name, "_pnl"]
        if pnl_val is None:
            color = "color: gray"
        elif pnl_val >= 0:
            color = "color: lime"
        else:
            color = "color: red"
        return [color] * len(row)

    styled = display.style.apply(_color_row, axis=1)
    st.dataframe(styled, use_container_width=True, height=320)

    # Summary stats for completed trades
    completed = tbl[tbl["_pnl"].notna()]
    if not completed.empty:
        wins = (completed["_pnl"] > 0).sum()
        total = len(completed)

        # Exit reason breakdown
        if exit_reasons is not None:
            reason_counts = completed.apply(
                lambda r: r["Exit Reason"], axis=1
            ).value_counts()
        else:
            reason_counts = pd.Series(dtype=int)

        col1, col2, col3 = st.columns(3)
        col1.metric("Trades Shown", total)
        col2.metric("Win Rate", f"{wins / total * 100:.1f}%" if total else "—")
        col3.metric(
            "Total P&L",
            f"${completed['_pnl'].sum() / 100 * initial_cash * _POSITION_FRACTION:+,.0f}",
        )

        if not reason_counts.empty:
            st.caption(
                "  ·  ".join(f"{k}: {v}" for k, v in reason_counts.items())
            )
