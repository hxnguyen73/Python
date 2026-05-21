from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
import yaml

_STRATEGIES_YAML = Path(__file__).parents[2] / "config" / "strategies.yaml"


def _load_yaml_overrides(strategy_name: str) -> dict:
    if not _STRATEGIES_YAML.exists():
        return {}
    with open(_STRATEGIES_YAML) as f:
        data = yaml.safe_load(f) or {}
    return data.get(strategy_name, {})


class BaseStrategy(ABC):
    """Abstract base that all strategies must subclass.

    Subclasses declare PARAMS as a class-level dict; the constructor merges
    defaults → strategies.yaml overrides → any runtime params passed in.

    Implement generate_entries() and generate_exits() independently so the
    dashboard can mix entry and exit strategies from different classes.
    The legacy generate_signals() is kept for backward compatibility and
    delegates to the two methods above by default.
    """

    PARAMS: dict[str, dict] = {}
    name: str = ""

    def __init__(self, params: dict | None = None) -> None:
        defaults = {k: v["default"] for k, v in self.PARAMS.items()}
        yaml_overrides = _load_yaml_overrides(self.name)
        runtime = params or {}
        self.params: dict = {**defaults, **yaml_overrides, **runtime}

    # ── Entry / Exit split ─────────────────────────────────────────────────

    def generate_entries(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned to df.index: 1=entry signal, 0=nothing.

        Default implementation extracts entries from generate_signals().
        Override for a clean implementation.
        """
        return (self.generate_signals(df) == 1).astype(int)

    def generate_exits(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned to df.index: 1=exit signal, 0=nothing.

        Default implementation extracts exits from generate_signals().
        Override for a clean implementation.
        """
        return (self.generate_signals(df) == -1).astype(int)

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned to df.index: 1=entry, -1=exit, 0=hold.

        Kept for backward compatibility with custom user strategies that
        implement only this method.
        """

    def thinkscript_body(self) -> str:
        """Return a strategy-specific ThinkScript snippet.

        Default returns empty string; the exporter falls back to a generic template.
        """
        return ""
