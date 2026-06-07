from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def make_ohlcv(n: int = 200, freq: str = "1min", seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-02 09:30", periods=n, freq=freq, tz="UTC")
    close = 100 + np.cumsum(rng.normal(0, 0.1, n))
    high = close + rng.uniform(0, 0.5, n)
    low = close - rng.uniform(0, 0.5, n)
    open_ = close - rng.normal(0, 0.1, n)
    volume = rng.integers(10_000, 100_000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    return make_ohlcv()
