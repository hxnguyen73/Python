from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.strategies.base_strategy import BaseStrategy
from src.strategies.registry import registry

_STRATEGIES_YAML = Path(__file__).parents[3] / "config" / "strategies.yaml"


def render_strategy_editor(strategy_name: str) -> dict:
    """Render dynamic parameter controls for the given strategy.

    Returns the current parameter values (including any live edits).
    """
    cls = registry.get(strategy_name)
    params_def = cls.PARAMS

    if not params_def:
        st.info("This strategy has no configurable parameters.")
        return {}

    st.subheader(f"Strategy Editor — {strategy_name}")
    current_params = _load_yaml_params(strategy_name)
    live_params = {}

    for key, spec in params_def.items():
        param_type = spec.get("type", "float")
        default = current_params.get(key, spec.get("default"))
        label = key.replace("_", " ").title()

        if param_type == "int":
            live_params[key] = st.slider(
                label,
                min_value=spec.get("min", 1),
                max_value=spec.get("max", 100),
                value=int(default),
                step=spec.get("step", 1),
            )
        elif param_type == "float":
            live_params[key] = st.number_input(
                label,
                min_value=float(spec.get("min", 0.0)),
                max_value=float(spec.get("max", 1.0)),
                value=float(default),
                step=float(spec.get("step", 0.001)),
                format="%.4f",
            )
        elif param_type == "bool":
            live_params[key] = st.toggle(label, value=bool(default))
        elif param_type == "select":
            options = spec.get("options", [])
            idx = options.index(default) if default in options else 0
            live_params[key] = st.selectbox(label, options=options, index=idx)
        else:
            live_params[key] = st.text_input(label, value=str(default))

    if st.button("Save Parameters"):
        _save_yaml_params(strategy_name, live_params)
        st.success("Parameters saved to strategies.yaml")

    return live_params


def _load_yaml_params(strategy_name: str) -> dict:
    if not _STRATEGIES_YAML.exists():
        return {}
    with open(_STRATEGIES_YAML) as f:
        data = yaml.safe_load(f) or {}
    return data.get(strategy_name, {})


def _save_yaml_params(strategy_name: str, params: dict) -> None:
    data: dict = {}
    if _STRATEGIES_YAML.exists():
        with open(_STRATEGIES_YAML) as f:
            data = yaml.safe_load(f) or {}
    data[strategy_name] = params
    with open(_STRATEGIES_YAML, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
