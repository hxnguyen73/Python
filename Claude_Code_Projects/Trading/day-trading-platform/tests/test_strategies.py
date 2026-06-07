from __future__ import annotations

import pandas as pd
import pytest

from tests.conftest import make_ohlcv
from src.strategies.vwap_strategy import VWAPStrategy
from src.strategies.macd_ema_strategy import MACDEMAStrategy
from src.strategies.orb_strategy import ORBStrategy
from src.strategies.rsi_strategy import RSIStrategy


@pytest.fixture
def df() -> pd.DataFrame:
    return make_ohlcv(300)


def _assert_signal_contract(signals: pd.Series, df: pd.DataFrame) -> None:
    assert isinstance(signals, pd.Series)
    assert signals.index.equals(df.index), "Signal index must match df index"
    assert set(signals.unique()).issubset({-1, 0, 1}), "Signals must be -1, 0, or 1"


class TestVWAPStrategy:
    def test_returns_valid_signals(self, df):
        strat = VWAPStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_default_params_applied(self):
        strat = VWAPStrategy()
        assert strat.params["vwap_buffer_pct"] == VWAPStrategy.PARAMS["vwap_buffer_pct"]["default"]

    def test_runtime_param_override(self):
        strat = VWAPStrategy(params={"volume_multiplier": 3.0})
        assert strat.params["volume_multiplier"] == 3.0

    def test_thinkscript_body_not_empty(self):
        assert VWAPStrategy().thinkscript_body() != ""


class TestMACDEMAStrategy:
    def test_returns_valid_signals(self, df):
        strat = MACDEMAStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_thinkscript_body_not_empty(self):
        assert MACDEMAStrategy().thinkscript_body() != ""


class TestORBStrategy:
    def test_returns_valid_signals(self, df):
        strat = ORBStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_range_minutes_select_param(self):
        strat = ORBStrategy(params={"range_minutes": 5})
        assert strat.params["range_minutes"] == 5

    def test_thinkscript_body_not_empty(self):
        assert ORBStrategy().thinkscript_body() != ""


class TestRSIStrategy:
    def test_returns_valid_signals(self, df):
        strat = RSIStrategy()
        sigs = strat.generate_signals(df)
        _assert_signal_contract(sigs, df)

    def test_oversold_level_param(self):
        strat = RSIStrategy(params={"oversold_level": 25.0})
        assert strat.params["oversold_level"] == 25.0

    def test_thinkscript_body_not_empty(self):
        assert RSIStrategy().thinkscript_body() != ""
