"""Training utilities for the historical player-points model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from data.leakage import get_pre_deadline_history
from prediction.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, build_feature_frame
from prediction.model import PlayerPointsModel


def train_model(
    player_gameweeks: pd.DataFrame,
    *,
    as_of_season: str | None = None,
    as_of_gameweek: int | None = None,
    random_state: int = 42,
) -> PlayerPointsModel:
    """Fit a point model using only outcomes available before an optional cutoff.

    Pass both cutoff arguments for historical backtests. At cutoff ``season, gameweek``,
    only earlier Gameweeks and earlier seasons may contribute target labels.
    """
    if (as_of_season is None) != (as_of_gameweek is None):
        raise ValueError("as_of_season and as_of_gameweek must be supplied together")
    if "total_points" not in player_gameweeks.columns:
        raise ValueError("player_gameweeks must contain the total_points target column")

    if as_of_season is not None and as_of_gameweek is not None:
        training_data = get_pre_deadline_history(
            player_gameweeks, current_season=as_of_season, current_gameweek=as_of_gameweek
        )
    else:
        training_data = player_gameweeks.copy()
    training_data = training_data.loc[training_data["total_points"].notna()].reset_index(drop=True)
    if training_data.empty:
        raise ValueError("No historical Gameweek outcomes are available before the training cutoff")

    feature_frame = build_feature_frame(training_data)
    target = pd.to_numeric(training_data["total_points"], errors="coerce")
    valid_target = target.notna()
    feature_frame = feature_frame.loc[valid_target].reset_index(drop=True)
    target = target.loc[valid_target].reset_index(drop=True)

    estimator = _new_estimator(random_state)
    estimator.fit(feature_frame.loc[:, list(FEATURE_COLUMNS)], target)

    seasons = tuple(sorted(training_data["season"].astype(str).unique()))
    calibration_residuals: tuple[float, ...] = ()
    calibration_residuals_by_position: dict[str, tuple[float, ...]] = {}
    calibration_season: str | None = None
    if len(seasons) >= 2:
        calibration_season = seasons[-1]
        calibration_training = training_data.loc[
            training_data["season"].astype(str) < calibration_season
        ].reset_index(drop=True)
        calibration_data = training_data.loc[
            training_data["season"].astype(str) == calibration_season
        ].reset_index(drop=True)
        if not calibration_training.empty and not calibration_data.empty:
            calibration_estimator = _new_estimator(random_state)
            calibration_features = build_feature_frame(calibration_training)
            calibration_target = pd.to_numeric(calibration_training["total_points"], errors="coerce")
            calibration_estimator.fit(
                calibration_features.loc[:, list(FEATURE_COLUMNS)], calibration_target
            )
            heldout_features = build_feature_frame(calibration_data)
            heldout_prediction = np.clip(
                calibration_estimator.predict(heldout_features.loc[:, list(FEATURE_COLUMNS)]),
                a_min=0.0,
                a_max=None,
            )
            errors = pd.to_numeric(calibration_data["total_points"]).to_numpy(dtype=float) - heldout_prediction
            calibration_residuals = tuple(float(error) for error in errors)
            calibration_positions = calibration_data.get(
                "position", pd.Series("unknown", index=calibration_data.index)
            ).fillna("unknown").astype(str).str.upper()
            calibration_frame = pd.DataFrame(
                {"position": calibration_positions.to_numpy(), "residual": errors}
            )
            calibration_residuals_by_position = {
                position: tuple(float(error) for error in group["residual"].to_numpy())
                for position, group in calibration_frame.groupby("position", sort=True)
            }

    return PlayerPointsModel(
        estimator=estimator,
        training_seasons=seasons,
        as_of_season=as_of_season,
        as_of_gameweek=as_of_gameweek,
        training_rows=len(target),
        baseline_points=float(target.mean()),
        calibration_residuals=calibration_residuals,
        calibration_residuals_by_position=calibration_residuals_by_position,
        calibration_season=calibration_season if calibration_residuals else None,
    )


def _new_estimator(random_state: int) -> Pipeline:
    """Create a fresh instance of the project's point model pipeline."""
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median", add_indicator=True), list(NUMERIC_FEATURES)),
            ("categorical", categorical_pipeline, list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline(
        steps=[
            ("features", preprocessor),
            (
                "regressor",
                HistGradientBoostingRegressor(
                    learning_rate=0.06,
                    max_iter=120,
                    max_leaf_nodes=15,
                    l2_regularization=1.0,
                    early_stopping=False,
                    random_state=random_state,
                ),
            ),
        ]
    )
