from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Type

from src.strategies.base_strategy import BaseStrategy

_BUILTIN_DIR = Path(__file__).parent
_USER_DIR = _BUILTIN_DIR / "user_strategies"


class StrategyRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Type[BaseStrategy]] = {}
        self._discovered = False

    def _discover(self) -> None:
        if self._discovered:
            return
        self._discovered = True
        _scan_package("src.strategies", _BUILTIN_DIR, exclude={"registry", "base_strategy", "indicators"})
        _scan_package("src.strategies.user_strategies", _USER_DIR, exclude=set())
        for cls in BaseStrategy.__subclasses__():
            _register_cls(self._registry, cls)

    def register(self, cls: Type[BaseStrategy]) -> None:
        _register_cls(self._registry, cls)

    def list(self) -> list[str]:
        self._discover()
        return sorted(self._registry.keys())

    def get(self, name: str) -> Type[BaseStrategy]:
        self._discover()
        if name not in self._registry:
            raise KeyError(f"Strategy '{name}' not found. Available: {self.list()}")
        return self._registry[name]

    def build(self, name: str, params: dict | None = None) -> BaseStrategy:
        cls = self.get(name)
        return cls(params=params)


def _register_cls(reg: dict, cls: Type[BaseStrategy]) -> None:
    if inspect.isabstract(cls):
        return
    key = getattr(cls, "name", "") or _to_snake(cls.__name__)
    cls.name = key
    reg[key] = cls
    # Recurse into subclasses registered after import
    for sub in cls.__subclasses__():
        _register_cls(reg, sub)


def _to_snake(name: str) -> str:
    """Convert CamelCase class name to snake_case registry key."""
    import re
    name = re.sub(r"Strategy$", "", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.lower()


def _scan_package(package: str, directory: Path, exclude: set[str]) -> None:
    for finder, module_name, _ in pkgutil.iter_modules([str(directory)]):
        if module_name in exclude or module_name.startswith("_"):
            continue
        full_name = f"{package}.{module_name}"
        try:
            importlib.import_module(full_name)
        except Exception as exc:  # noqa: BLE001
            print(f"[registry] Could not import {full_name}: {exc}")


registry = StrategyRegistry()
