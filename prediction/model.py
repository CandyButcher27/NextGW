"""Shared model types used by training and inference without importing training code."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.pipeline import Pipeline

MIN_POSITION_CALIBRATION_RESIDUALS = 30


@dataclass
class PlayerPointsModel:
    """Fitted point model, training metadata, and chronological calibration residuals."""

    estimator: Pipeline
    training_seasons: tuple[str, ...]
    as_of_season: str | None
    as_of_gameweek: int | None
    training_rows: int
    baseline_points: float
    calibration_residuals: tuple[float, ...]
    calibration_residuals_by_position: dict[str, tuple[float, ...]]
    calibration_season: str | None

    def calibration_for_position(
        self, position: str | None
    ) -> tuple[tuple[float, ...], str]:
        """Return residuals by position, falling back to pooled residuals if sparse."""
        key = str(position).upper() if position is not None else "UNKNOWN"
        position_residuals = self.calibration_residuals_by_position.get(key, ())
        if len(position_residuals) >= MIN_POSITION_CALIBRATION_RESIDUALS:
            return position_residuals, "position"
        if len(self.calibration_residuals) >= 2:
            return self.calibration_residuals, "pooled_fallback"
        return (), "unavailable"
