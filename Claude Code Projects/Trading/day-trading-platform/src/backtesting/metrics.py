from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    win_rate: float           # primary metric
    total_trades: int
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    total_return: float

    def summary(self) -> dict:
        return {
            "Win Rate": f"{self.win_rate:.1%}",
            "Total Trades": self.total_trades,
            "Expectancy": f"${self.expectancy:.2f}",
            "Max Drawdown": f"{self.max_drawdown:.1%}",
            "Sharpe Ratio": f"{self.sharpe_ratio:.2f}",
            "Avg Win": f"${self.avg_win:.2f}",
            "Avg Loss": f"${self.avg_loss:.2f}",
            "Total Return": f"{self.total_return:.1%}",
        }


def compute_metrics(portfolio) -> BacktestMetrics:
    """Compute BacktestMetrics from a VectorBT Portfolio object."""
    trades = portfolio.trades.records_readable
    if trades.empty:
        return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0)

    pnl = trades["PnL"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]

    total = len(pnl)
    win_rate = len(wins) / total if total else 0
    avg_win = float(wins.mean()) if len(wins) else 0
    avg_loss = float(losses.mean()) if len(losses) else 0
    loss_rate = 1 - win_rate
    expectancy = avg_win * win_rate + avg_loss * loss_rate

    returns = portfolio.returns()
    sharpe = _sharpe(returns)
    max_dd = float(portfolio.max_drawdown())
    total_ret = float(portfolio.total_return())

    return BacktestMetrics(
        win_rate=win_rate,
        total_trades=total,
        expectancy=expectancy,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        avg_win=avg_win,
        avg_loss=avg_loss,
        total_return=total_ret,
    )


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))
