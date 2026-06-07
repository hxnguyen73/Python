from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.conftest import make_ohlcv


class TestDataManager:
    def test_get_bars_uses_cache(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

        sample_df = make_ohlcv(100)

        with patch("src.data.data_manager.fetch_bars", return_value=sample_df) as mock_fetch:
            from src.data import data_manager

            # Patch cache dir to tmp_path
            with patch("src.data.data_manager._load_settings") as mock_settings:
                mock_settings.return_value = {
                    "data": {"cache_enabled": True, "cache_dir": str(tmp_path), "feed": "iex"},
                    "default_timeframe": "5Min",
                }
                result1 = data_manager.get_bars("AAPL", "2024-01-01", "2024-06-01")
                result2 = data_manager.get_bars("AAPL", "2024-01-01", "2024-06-01")

        assert mock_fetch.call_count == 1, "Should only fetch once when cache is available"
        assert len(result1) == len(sample_df)

    def test_get_bars_force_refresh(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

        sample_df = make_ohlcv(100)

        with patch("src.data.data_manager.fetch_bars", return_value=sample_df) as mock_fetch:
            from src.data import data_manager

            with patch("src.data.data_manager._load_settings") as mock_settings:
                mock_settings.return_value = {
                    "data": {"cache_enabled": True, "cache_dir": str(tmp_path), "feed": "iex"},
                    "default_timeframe": "5Min",
                }
                data_manager.get_bars("AAPL", "2024-01-01", "2024-06-01")
                data_manager.get_bars("AAPL", "2024-01-01", "2024-06-01", force_refresh=True)

        assert mock_fetch.call_count == 2

    def test_normalize_converts_to_float64(self):
        from src.data.data_manager import _normalize
        df = make_ohlcv(10).astype("float32")
        _normalize(df)
        assert df["close"].dtype == "float64"
