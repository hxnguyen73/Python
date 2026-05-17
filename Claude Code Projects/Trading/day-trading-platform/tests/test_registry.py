from __future__ import annotations

import pytest

from src.strategies.registry import StrategyRegistry, registry
from src.strategies.base_strategy import BaseStrategy


class TestStrategyRegistry:
    def test_list_includes_builtins(self):
        names = registry.list()
        for expected in ["vwap", "macd_ema", "orb", "rsi"]:
            assert expected in names, f"Expected '{expected}' in registry"

    def test_get_returns_correct_class(self):
        from src.strategies.vwap_strategy import VWAPStrategy
        assert registry.get("vwap") is VWAPStrategy

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError):
            registry.get("does_not_exist_xyz")

    def test_build_returns_instance(self):
        strat = registry.build("rsi")
        assert isinstance(strat, BaseStrategy)

    def test_build_with_params(self):
        strat = registry.build("vwap", params={"volume_multiplier": 2.5})
        assert strat.params["volume_multiplier"] == 2.5

    def test_fresh_registry_discovers_builtins(self):
        fresh = StrategyRegistry()
        names = fresh.list()
        assert "vwap" in names

    def test_strategy_name_set_on_class(self):
        registry.list()  # trigger discovery
        from src.strategies.vwap_strategy import VWAPStrategy
        assert VWAPStrategy.name == "vwap"
