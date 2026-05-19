from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.backtesting.evaluate_backtest import evaluate as _evaluate_quality


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
    # Backtest-Expert quality evaluation (auto-populated)
    quality: dict = field(default_factory=dict)

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

    @property
    def verdict(self) -> str:
        return self.quality.get("verdict", "N/A")

    @property
    def quality_score(self) -> int:
        return self.quality.get("total_score", 0)


def compute_metrics(
    portfolio,
    years_tested: float = 1.0,
    num_parameters: int = 3,
    commission: float = 0.001,
) -> BacktestMetrics:
    """Compute BacktestMetrics from a VectorBT Portfolio object.

    Automatically runs the Backtest-Expert 5-dimension quality evaluation.
    """
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

    # Backtest-Expert evaluation — convert $ avg_win/loss to % of portfolio value
    # approximate: use portfolio initial value for % conversion
    init_value = float(portfolio.init_cash)
    avg_win_pct = (avg_win / init_value * 100) if init_value and avg_win else 0.0
    avg_loss_pct = abs(avg_loss / init_value * 100) if init_value and avg_loss else 0.0

    try:
        quality = _evaluate_quality(
            total_trades=total,
            win_rate=win_rate * 100,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            max_drawdown_pct=abs(max_dd) * 100,
            years_tested=max(1, int(years_tested)),
            num_parameters=num_parameters,
            slippage_tested=commission > 0,
        )
    except Exception:
        quality = {}

    return BacktestMetrics(
        win_rate=win_rate,
        total_trades=total,
        expectancy=expectancy,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        avg_win=avg_win,
        avg_loss=avg_loss,
        total_return=total_ret,
        quality=quality,
    )


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))
