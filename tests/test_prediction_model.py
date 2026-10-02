"""Tests for feature leakage, cutoff handling, prediction, and temporal evaluation."""

import pandas as pd
import pytest

from data.schema import PERFORMANCE_COLUMNS
from prediction import (
    build_feature_frame,
    evaluate_model,
    predict_gameweek,
    predict_player_points,
    train_model,
)


def _historical_data() -> pd.DataFrame:
    rows = []
    seasons = ["2022-23", "2023-24", "2024-25"]
    for season_index, season in enumerate(seasons):
        for gameweek in range(1, 7):
            for player_id in range(1, 5):
                points = (player_id + gameweek + season_index) % 9
                rows.append(
                    {
                        "season": season,
                        "gameweek": gameweek,
                        "player_id": player_id,
                        "player_name": f"Player {player_id}",
                        "web_name": f"P{player_id}",
                        "team": f"Team {(player_id % 3) + 1}",
                        "team_id": (player_id % 3) + 1,
                        "position": ["GK", "DEF", "MID", "FWD"][player_id - 1],
                        "element_type": player_id,
                        "price": 5.0,
                        "opponent_team": f"Team {(player_id + gameweek) % 3 + 1}",
                        "opponent_team_id": (player_id + gameweek) % 3 + 1,
                        "was_home": bool(gameweek % 2),
                        "matches_in_gw": 1,
                        "minutes": 90 if points else 0,
                        "total_points": points,
                        "expected_goals": points / 10,
                        "expected_assists": points / 20,
                        "expected_goal_involvements": points / 8,
                        "expected_goals_conceded": 0.5,
                        "bonus": points // 3,
                        "bps": points * 4,
                    }
                )
    return pd.DataFrame(rows)


def test_features_use_shifted_history_and_exclude_raw_outcomes() -> None:
    data = _historical_data()
    features = build_feature_frame(data)
    row = features.loc[
        (features["season"] == "2023-24")
        & (features["gameweek"] == 3)
        & (features["player_id"] == 1)
    ].iloc[0]
    previous = data.loc[
        (data["season"] == "2023-24")
        & (data["gameweek"] == 2)
        & (data["player_id"] == 1),
        "total_points",
    ].iloc[0]
    assert row["total_points_lag_1"] == previous
    assert "total_points" not in features.columns
    assert "minutes" not in features.columns
    assert "price" not in features.columns


def test_current_gameweek_outcome_does_not_change_its_features() -> None:
    data = _historical_data()
    original = build_feature_frame(data)
    changed = data.copy()
    target = (changed["season"] == "2023-24") & (changed["gameweek"] == 4)
    changed.loc[target, ["total_points", "minutes", "expected_goals"]] = 999
    updated = build_feature_frame(changed)
    key = (original["season"] == "2023-24") & (original["gameweek"] == 4)
    pd.testing.assert_frame_equal(
        original.loc[key].reset_index(drop=True), updated.loc[key].reset_index(drop=True)
    )


def test_target_gameweek_realized_performance_cannot_change_prediction_features() -> None:
    data = _historical_data()
    target_mask = (data["season"] == "2023-24") & (data["gameweek"] == 4)
    fixtures = data.loc[target_mask].copy()
    model = train_model(data, as_of_season="2023-24", as_of_gameweek=4)

    original_features = build_feature_frame(data).loc[target_mask].reset_index(drop=True)
    original_predictions = predict_gameweek(model, data, fixtures)["predicted_points"]

    changed = data.copy()
    realized_columns = [column for column in PERFORMANCE_COLUMNS if column in changed.columns]
    changed.loc[target_mask, realized_columns] = 999
    changed_fixtures = changed.loc[target_mask].copy()
    changed_features = build_feature_frame(changed).loc[target_mask].reset_index(drop=True)
    changed_predictions = predict_gameweek(model, changed, changed_fixtures)["predicted_points"]

    pd.testing.assert_frame_equal(original_features, changed_features)
    pd.testing.assert_series_equal(original_predictions, changed_predictions)


def test_future_gameweek_outcomes_do_not_change_earlier_features() -> None:
    data = _historical_data()
    original = build_feature_frame(data)
    changed = data.copy()
    future = (changed["season"] == "2023-24") & (changed["gameweek"] > 3)
    changed.loc[future, ["total_points", "minutes", "expected_goals"]] = 999
    updated = build_feature_frame(changed)
    target = (original["season"] == "2023-24") & (original["gameweek"] == 3)
    pd.testing.assert_frame_equal(
        original.loc[target].reset_index(drop=True), updated.loc[target].reset_index(drop=True)
    )


def test_training_cutoff_excludes_current_and_later_gameweeks() -> None:
    data = _historical_data()
    model = train_model(data, as_of_season="2023-24", as_of_gameweek=3)
    assert model.training_rows == 32  # 2022-23 plus GW 1 and 2 of 2023-24
    assert model.training_seasons == ("2022-23", "2023-24")
    with pytest.raises(ValueError, match="must be supplied together"):
        train_model(data, as_of_season="2023-24")


def test_prediction_ignores_fixture_outcomes_and_returns_nonnegative_points() -> None:
    data = _historical_data()
    model = train_model(data, as_of_season="2024-25", as_of_gameweek=1)
    fixtures = data.loc[(data["season"] == "2024-25") & (data["gameweek"] == 3)].copy()
    normal = predict_gameweek(model, data, fixtures)
    fixtures["total_points"] = 10000
    leaked = predict_gameweek(model, data, fixtures)
    assert normal["predicted_points"].ge(0).all()
    pd.testing.assert_series_equal(normal["predicted_points"], leaked["predicted_points"])


def test_predict_single_player_and_evaluate_latest_season() -> None:
    data = _historical_data()
    model = train_model(data, as_of_season="2024-25", as_of_gameweek=1)
    points = predict_player_points(
        model,
        data,
        player_id=1,
        season="2024-25",
        gameweek=2,
        fixture_context={"opponent_team": "Team 2", "was_home": True},
    )
    assert points >= 0

    metrics = evaluate_model(data)
    assert metrics["test_season"] == "2024-25"
    assert metrics["training_seasons"] == ["2022-23", "2023-24"]
    assert metrics["n_predictions"] == 24
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0
    assert metrics["test_season"] == "2024-25"
    assert metrics["minutes_aware_baseline_mae"] >= 0
    assert set(metrics["by_minutes"]) == {"regular_high_minutes", "low_minutes"}
    assert sum(group["n"] for group in metrics["by_minutes"].values()) == 24
    assert set(metrics["by_position"]) == {"GK", "DEF", "MID", "FWD"}
    assert sum(group["n"] for group in metrics["by_position"].values()) == 24
    assert metrics["uncertainty_calibration"]["status"] == "PROVISIONAL — coverage has not been measured"
