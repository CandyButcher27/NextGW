"""Tests for the proposed planner-facing Predictor API."""

import pandas as pd
import pytest

from prediction import Predictor, save_predictor_artifact, train_model
from test_prediction_model import _historical_data


def test_predictor_load_player_and_horizon_interface(tmp_path) -> None:
    data = _historical_data()
    model = train_model(data, as_of_season="2024-25", as_of_gameweek=1)
    fixtures = data.loc[(data["season"] == "2024-25") & (data["gameweek"].between(2, 5))].copy()
    path = save_predictor_artifact(
        tmp_path / "predictor.pkl", model, data, fixtures, season="2024-25"
    )

    predictor = Predictor.load(path)
    one = predictor.predict_player_gw(player_id=1, gameweek=2)
    assert one["pred_mean"] >= 0
    assert one["pred_std"] is not None
    assert one["uncertainty_status"].startswith("PROVISIONAL —")
    assert "coverage has not been measured" in one["uncertainty_status"]
    assert set(one["quantiles"]) == {"p10", "p25", "p50", "p75", "p90"}
    assert list(one["quantiles"].values()) == sorted(one["quantiles"].values())

    horizon = predictor.predict_horizon("2024-25", as_of_gw=1)
    assert set(horizon["gameweek"]) == {2, 3, 4, 5}
    assert {"pred_mean", "pred_std", "quantiles", "uncertainty_status"}.issubset(horizon.columns)
    assert horizon["uncertainty_status"].str.startswith("PROVISIONAL —").all()
    assert len(horizon) == 16


def test_horizon_uses_only_history_available_at_origin() -> None:
    data = _historical_data()
    model = train_model(data, as_of_season="2024-25", as_of_gameweek=1)
    fixtures = data.loc[(data["season"] == "2024-25") & (data["gameweek"].between(3, 4))].copy()
    original = Predictor(model, data, fixtures, "2024-25").predict_horizon(
        "2024-25", as_of_gw=2, horizon=2
    )

    changed_history = data.copy()
    future_actuals = (changed_history["season"] == "2024-25") & (changed_history["gameweek"] > 2)
    changed_history.loc[future_actuals, ["total_points", "minutes", "expected_goals"]] = 999
    changed = Predictor(model, changed_history, fixtures, "2024-25").predict_horizon(
        "2024-25", as_of_gw=2, horizon=2
    )
    pd.testing.assert_frame_equal(original, changed)


def test_predictor_rejects_later_training_cutoff_and_bad_horizon() -> None:
    data = _historical_data()
    later_model = train_model(data, as_of_season="2024-25", as_of_gameweek=4)
    predictor = Predictor(later_model, data, pd.DataFrame(), "2024-25")
    with pytest.raises(ValueError, match="later than the requested horizon origin"):
        predictor.predict_horizon("2024-25", as_of_gw=2)
    earlier_model = train_model(data, as_of_season="2024-25", as_of_gameweek=1)
    with pytest.raises(ValueError, match="horizon must be at least 1"):
        Predictor(earlier_model, data, pd.DataFrame(), "2024-25").predict_horizon(
            "2024-25", as_of_gw=2, horizon=0
        )
