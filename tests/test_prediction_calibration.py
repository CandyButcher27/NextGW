"""Tests for position-specific residual calibration and inference isolation."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from prediction import Predictor, train_model
from prediction.model import PlayerPointsModel
from test_prediction_model import _historical_data


class _FixedEstimator:
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        return np.full(len(features), 4.0)


def _model() -> PlayerPointsModel:
    return PlayerPointsModel(
        estimator=_FixedEstimator(),
        training_seasons=("2022-23", "2023-24"),
        as_of_season="2024-25",
        as_of_gameweek=1,
        training_rows=20,
        baseline_points=4.0,
        calibration_residuals=tuple(float(value) for value in range(100)),
        calibration_residuals_by_position={
            "FWD": tuple(float(value) for value in range(30)),
            "GK": (1.0, 2.0, 3.0),
        },
        calibration_season="2023-24",
    )


def _history_and_fixtures() -> tuple[pd.DataFrame, pd.DataFrame]:
    history = pd.DataFrame(
        [
            {"season": "2023-24", "gameweek": 1, "player_id": 10, "position": "FWD", "team": "A", "total_points": 5, "minutes": 90},
            {"season": "2023-24", "gameweek": 1, "player_id": 20, "position": "GK", "team": "B", "total_points": 4, "minutes": 90},
        ]
    )
    fixtures = pd.DataFrame(
        [
            {"season": "2024-25", "gameweek": 1, "player_id": 10, "position": "FWD", "team": "A", "opponent_team": "B", "was_home": True, "matches_in_gw": 1},
            {"season": "2024-25", "gameweek": 1, "player_id": 20, "position": "GK", "team": "B", "opponent_team": "A", "was_home": False, "matches_in_gw": 1},
        ]
    )
    return history, fixtures


def test_inference_import_does_not_import_training_module() -> None:
    code = "import sys; import prediction.predictor; assert 'prediction.train' not in sys.modules"
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )


def test_training_saves_chronological_residuals_by_position() -> None:
    model = train_model(_historical_data(), as_of_season="2024-25", as_of_gameweek=1)
    assert model.training_seasons == ("2022-23", "2023-24")
    assert model.calibration_season == "2023-24"
    assert set(model.calibration_residuals_by_position) == {"GK", "DEF", "MID", "FWD"}
    assert all(len(values) == 6 for values in model.calibration_residuals_by_position.values())
    residuals, source = model.calibration_for_position("FWD")
    assert source == "pooled_fallback"  # six position residuals are below the documented minimum
    assert residuals == model.calibration_residuals


def test_forecast_uses_position_residuals_and_pooled_fallback() -> None:
    history, fixtures = _history_and_fixtures()
    predictor = Predictor(_model(), history, fixtures, "2024-25")

    forward = predictor.predict_player_gw(10, 1)
    goalkeeper = predictor.predict_player_gw(20, 1)
    assert forward["uncertainty_status"].startswith("PROVISIONAL — position calibration for FWD")
    assert forward["pred_std"] == pytest.approx(np.std(np.arange(30), ddof=1))
    assert goalkeeper["uncertainty_status"].startswith("PROVISIONAL — pooled_fallback calibration for GK")
    assert goalkeeper["pred_std"] == pytest.approx(np.std(np.arange(100), ddof=1))