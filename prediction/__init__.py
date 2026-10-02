"""Leakage-safe FPL player-point prediction with lazy public exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "PlayerPointsModel": ("model", "PlayerPointsModel"),
    "Predictor": ("predictor", "Predictor"),
    "build_feature_frame": ("features", "build_feature_frame"),
    "evaluate_model": ("evaluate", "evaluate_model"),
    "predict_gameweek": ("predict", "predict_gameweek"),
    "predict_player_points": ("predict", "predict_player_points"),
    "save_predictor_artifact": ("predictor", "save_predictor_artifact"),
    "train_model": ("train", "train_model"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load exports only when requested so inference imports do not load training code."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(f".{module_name}", __name__), attribute)
    globals()[name] = value
    return value
