from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable

import pandas as pd

from src.strategies.base_strategy import BaseStrategy


class AlertManager:
    """Watches for new signals on a live DataFrame and fires callbacks."""

    def __init__(self, strategy: BaseStrategy) -> None:
        self.strategy = strategy
        self._callbacks: list[Callable[[str, datetime, float, int], None]] = []
        self._last_index = None
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[str, datetime, float, int], None]) -> None:
        """Register a callback(symbol, timestamp, price, signal_value)."""
        self._callbacks.append(callback)

    def check(self, symbol: str, df: pd.DataFrame) -> list[dict]:
        """Compute signals on df, fire callbacks for any new bar signals."""
        signals = self.strategy.generate_signals(df)
        new_signals = []

        with self._lock:
            if self._last_index is not None and self._last_index in signals.index:
                start_pos = signals.index.get_loc(self._last_index) + 1
                new_signals_series = signals.iloc[start_pos:]
            else:
                new_signals_series = signals.iloc[-1:]  # only the latest bar on first run

            self._last_index = signals.index[-1]

        for ts, val in new_signals_series.items():
            if val != 0:
                price = float(df.loc[ts, "close"])
                event = {
                    "symbol": symbol,
                    "timestamp": ts,
                    "price": price,
                    "signal": val,
                    "action": "ENTRY" if val == 1 else "EXIT",
                }
                new_signals.append(event)
                self._fire(symbol, ts, price, val)

        return new_signals

    def _fire(self, symbol: str, timestamp, price: float, signal: int) -> None:
        action = "ENTRY" if signal == 1 else "EXIT"
        _desktop_notify(f"{symbol} {action}", f"${price:.2f} at {timestamp}")
        for cb in self._callbacks:
            try:
                cb(symbol, timestamp, price, signal)
            except Exception:  # noqa: BLE001
                pass


def _desktop_notify(title: str, message: str) -> None:
    """Best-effort desktop notification — silently skips if unavailable."""
    try:
        import plyer
        plyer.notification.notify(title=title, message=message, timeout=5)
    except Exception:  # noqa: BLE001
        pass
