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
    """

    # Each entry: {"type": "int"|"float"|"bool"|"select", "default": ..., ...}
    PARAMS: dict[str, dict] = {}

    # Registry key — set automatically by the registry; override to customise.
    name: str = ""

    def __init__(self, params: dict | None = None) -> None:
        defaults = {k: v["default"] for k, v in self.PARAMS.items()}
        yaml_overrides = _load_yaml_overrides(self.name)
        runtime = params or {}
        self.params: dict = {**defaults, **yaml_overrides, **runtime}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned to df.index: 1=entry, -1=exit, 0=hold."""

    def thinkscript_body(self) -> str:
        """Return a strategy-specific ThinkScript snippet.

        Default returns empty string; the exporter falls back to a generic template.
        """
        return ""
