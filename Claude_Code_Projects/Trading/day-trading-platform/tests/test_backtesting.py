from __future__ import annotations

import pandas as pd
import pytest

from tests.conftest import make_ohlcv
from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.vwap_strategy import VWAPStrategy


@pytest.fixture
def df() -> pd.DataFrame:
    return make_ohlcv(500)


class TestMetrics:
    def test_zero_trades_returns_zeros(self):
        m = BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0)
        assert m.win_rate == 0
        assert m.total_trades == 0

    def test_summary_keys_in_order(self):
        m = BacktestMetrics(0.6, 10, 50.0, -0.05, 1.2, 100.0, -50.0, 0.25)
        keys = list(m.summary().keys())
        assert keys[0] == "Win Rate", "Win Rate must be first metric"
        assert keys[1] == "Total Trades"


class TestBacktestRunner:
    def test_run_returns_metrics(self, df):
        pytest.importorskip("vectorbt")
        from src.backtesting.backtest_runner import run
        strat = RSIStrategy()
        portfolio, metrics = run(strat, df)
        assert isinstance(metrics, BacktestMetrics)
        assert 0.0 <= metrics.win_rate <= 1.0
        assert metrics.total_trades >= 0

    def test_run_by_name(self, df):
        pytest.importorskip("vectorbt")
        from src.backtesting.backtest_runner import run
        portfolio, metrics = run("vwap", df)
        assert isinstance(metrics, BacktestMetrics)
