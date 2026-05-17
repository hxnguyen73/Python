from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.data.alpaca_client import fetch_bars

_CONFIG_PATH = Path(__file__).parents[2] / "config" / "settings.yaml"


def _load_settings() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _cache_path(cache_dir: Path, symbol: str, start: str, end: str, timeframe: str) -> Path:
    key = f"{symbol}_{start}_{end}_{timeframe}"
    h = hashlib.md5(key.encode()).hexdigest()[:8]
    return cache_dir / f"{symbol}_{timeframe}_{h}.parquet"


def get_bars(
    symbol: str,
    start: str | datetime,
    end: str | datetime,
    timeframe: str | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Return OHLCV bars, reading from disk cache when available.

    Caches to parquet under config.data.cache_dir.
    Always returns a DataFrame with columns: open, high, low, close, volume.
    """
    settings = _load_settings()
    data_cfg = settings.get("data", {})
    cache_enabled = data_cfg.get("cache_enabled", True)
    cache_dir = Path(data_cfg.get("cache_dir", "data/cache"))
    feed = data_cfg.get("feed", "iex")
    timeframe = timeframe or settings.get("default_timeframe", "5Min")

    start_str = start if isinstance(start, str) else start.date().isoformat()
    end_str = end if isinstance(end, str) else end.date().isoformat()

    if cache_enabled:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = _cache_path(cache_dir, symbol, start_str, end_str, timeframe)
        if path.exists() and not force_refresh:
            return pd.read_parquet(path)

    df = fetch_bars(symbol, start, end, timeframe=timeframe, feed=feed)
    _normalize(df)

    if cache_enabled and not df.empty:
        df.to_parquet(path)

    return df


def _normalize(df: pd.DataFrame) -> None:
    """Ensure OHLCV columns are float64; mutates in place."""
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = df[col].astype("float64")
