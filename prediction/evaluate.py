"""Chronological model evaluation for player Gameweek point forecasts."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from data.leakage import get_pre_deadline_history
from prediction.features import FEATURE_COLUMNS, build_feature_frame
from prediction.model import MIN_POSITION_CALIBRATION_RESIDUALS
from prediction.train import train_model

REGULAR_MINUTES_THRESHOLD = 60.0
MINUTES_BASELINE_WINDOW = 5


def evaluate_model(
    player_gameweeks: pd.DataFrame,
    test_season: str | None = None,
    *,
    random_state: int = 42,
) -> dict[str, object]:
    """Train on prior seasons and evaluate each test Gameweek before its deadline.

    The latest season is held out by default. At each test Gameweek, the model is
    queried with only history available before that Gameweek and fixture metadata.
    """
    seasons: Sequence[str] = tuple(sorted(player_gameweeks["season"].astype(str).unique()))
    if not seasons:
        raise ValueError("player_gameweeks is empty")
    selected_test_season = test_season or seasons[-1]
    if selected_test_season not in seasons:
        raise ValueError(f"test_season {selected_test_season!r} is not in the dataset")
    training_seasons = [season for season in seasons if season < selected_test_season]
    if not training_seasons:
        raise ValueError("At least one season before test_season is required")

    model = train_model(
        player_gameweeks,
        as_of_season=selected_test_season,
        as_of_gameweek=1,
        random_state=random_state,
    )
    test_data = player_gameweeks.loc[
        player_gameweeks["season"].astype(str) == selected_test_season
    ].copy().reset_index(drop=True)
    if test_data.empty:
        raise ValueError("The selected test season has no player Gameweek rows")

    test_features = build_feature_frame(test_data)
    y_true = pd.to_numeric(test_data["total_points"]).to_numpy(dtype=float)
    y_pred = np.clip(
        model.estimator.predict(test_features.loc[:, list(FEATURE_COLUMNS)]), a_min=0.0, a_max=None
    )
    mean_baseline = np.full_like(y_true, fill_value=model.baseline_points, dtype=float)
    minutes_baseline, minute_groups = _minutes_aware_baseline(
        player_gameweeks,
        test_data,
        selected_test_season,
        training_data=get_pre_deadline_history(
            player_gameweeks, current_season=selected_test_season, current_gameweek=1
        ),
    )
    score_all = np.ones(len(test_data), dtype=bool)
    overall = _score_group(y_true, y_pred, mean_baseline, minutes_baseline, score_all)
    by_minutes = {
        "regular_high_minutes": _score_group(
            y_true, y_pred, mean_baseline, minutes_baseline,
            minute_groups["regular_high_minutes"],
        ),
        "low_minutes": _score_group(
            y_true, y_pred, mean_baseline, minutes_baseline,
            minute_groups["low_minutes"],
        ),
    }
    positions = test_data["position"].fillna("unknown").astype(str).str.upper()
    by_position = {
        position: _score_group(
            y_true, y_pred, mean_baseline, minutes_baseline, positions.eq(position).to_numpy()
        )
        for position in sorted(positions.unique())
    }
    return {
        "mae": overall["model"]["mae"],
        "rmse": overall["model"]["rmse"],
        "baseline_mae": overall["training_mean_baseline"]["mae"],
        "minutes_aware_baseline_mae": overall["minutes_aware_baseline"]["mae"],
        "n_predictions": int(len(y_true)),
        "training_seasons": list(model.training_seasons),
        "test_season": selected_test_season,
        "features": list(FEATURE_COLUMNS),
        "config": {
            "model": "HistGradientBoostingRegressor",
            "random_state": random_state,
            "regular_minutes_threshold": REGULAR_MINUTES_THRESHOLD,
            "minutes_baseline_window": MINUTES_BASELINE_WINDOW,
        },
        "overall": overall,
        "by_minutes": by_minutes,
        "by_position": by_position,
        "uncertainty_calibration": {
            "method": "out-of-sample residuals by position with pooled fallback",
            "status": "PROVISIONAL — coverage has not been measured",
            "calibration_season": model.calibration_season,
            "n_residuals": len(model.calibration_residuals),
            "n_residuals_by_position": {
                position: len(residuals)
                for position, residuals in model.calibration_residuals_by_position.items()
            },
            "minimum_position_residuals": MIN_POSITION_CALIBRATION_RESIDUALS,
            "fallback": "pooled out-of-sample residuals if a position has fewer than the minimum",
        },
    }


def _score_group(
    actual: np.ndarray,
    model: np.ndarray,
    mean_baseline: np.ndarray,
    minutes_baseline: np.ndarray,
    mask: np.ndarray,
) -> dict[str, object]:
    """Score model and both baselines for the same subset of rows."""
    if not mask.any():
        empty = {"mae": None, "rmse": None}
        return {
            "n": 0,
            "model": empty.copy(),
            "training_mean_baseline": empty.copy(),
            "minutes_aware_baseline": empty.copy(),
        }
    return {
        "n": int(mask.sum()),
        "model": _regression_metrics(actual[mask], model[mask]),
        "training_mean_baseline": _regression_metrics(actual[mask], mean_baseline[mask]),
        "minutes_aware_baseline": _regression_metrics(actual[mask], minutes_baseline[mask]),
    }


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
    }


def _minutes_aware_baseline(
    player_gameweeks: pd.DataFrame,
    test_data: pd.DataFrame,
    test_season: str,
    *,
    training_data: pd.DataFrame,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Estimate points from pre-deadline expected minutes and recent points per minute."""
    numeric_training = training_data.copy()
    numeric_training["minutes"] = pd.to_numeric(numeric_training["minutes"], errors="coerce").fillna(0)
    numeric_training["total_points"] = pd.to_numeric(
        numeric_training["total_points"], errors="coerce"
    ).fillna(0)
    position_rate: dict[str, float] = {}
    position_minutes: dict[str, float] = {}
    for position, group in numeric_training.groupby("position", dropna=False):
        active = group.loc[group["minutes"] > 0]
        key = str(position).upper() if pd.notna(position) else "UNKNOWN"
        total_minutes = float(active["minutes"].sum())
        if total_minutes > 0:
            position_rate[key] = float(active["total_points"].sum() / total_minutes * 90.0)
        position_minutes[key] = float(group["minutes"].mean()) if not group.empty else 0.0
    global_active = numeric_training.loc[numeric_training["minutes"] > 0]
    global_rate = (
        float(global_active["total_points"].sum() / global_active["minutes"].sum() * 90.0)
        if not global_active.empty and global_active["minutes"].sum() > 0
        else 0.0
    )
    global_minutes = float(numeric_training["minutes"].mean()) if not numeric_training.empty else 0.0

    predictions = np.zeros(len(test_data), dtype=float)
    high_minutes = np.zeros(len(test_data), dtype=bool)
    for gameweek, fixture_indices in test_data.groupby("gameweek", sort=True).groups.items():
        history = get_pre_deadline_history(
            player_gameweeks, current_season=test_season, current_gameweek=int(gameweek)
        )
        histories = {
            player_id: group.sort_values(["season", "gameweek"])
            for player_id, group in history.groupby("player_id", sort=False)
        }
        for row_index in fixture_indices:
            row = test_data.loc[row_index]
            player_history = histories.get(row["player_id"])
            position = str(row.get("position", "unknown")).upper()
            if player_history is None or player_history.empty:
                recent = player_history
                expected_minutes = position_minutes.get(position, global_minutes)
                points_per_90 = position_rate.get(position, global_rate)
            else:
                recent = player_history.tail(MINUTES_BASELINE_WINDOW)
                recent_minutes = pd.to_numeric(recent["minutes"], errors="coerce").fillna(0)
                expected_minutes = float(recent_minutes.mean())
                high_minutes[row_index] = expected_minutes >= REGULAR_MINUTES_THRESHOLD
                active = player_history.loc[
                    pd.to_numeric(player_history["minutes"], errors="coerce").fillna(0) > 0
                ].tail(MINUTES_BASELINE_WINDOW)
                if active.empty:
                    points_per_90 = position_rate.get(position, global_rate)
                else:
                    active_minutes = pd.to_numeric(active["minutes"], errors="coerce").fillna(0)
                    active_points = pd.to_numeric(active["total_points"], errors="coerce").fillna(0)
                    points_per_90 = float(active_points.sum() / active_minutes.sum() * 90.0)
            matches = pd.to_numeric(pd.Series([row.get("matches_in_gw", 1)]), errors="coerce").iloc[0]
            matches = float(matches) if pd.notna(matches) and matches > 0 else 1.0
            expected_minutes = min(max(expected_minutes, 0.0), 90.0 * matches)
            predictions[row_index] = max(points_per_90, 0.0) * expected_minutes / 90.0

    return predictions, {
        "regular_high_minutes": high_minutes,
        "low_minutes": ~high_minutes,
    }
