"""Tests for data/leakage.py: strictly enforcing temporal leakage safety."""

import pandas as pd
import pytest

from data.leakage import (
    compute_leakage_safe_lags,
    get_pre_deadline_history,
    verify_no_future_leakage,
)


def _make_mock_history() -> pd.DataFrame:
    rows = []
    # 2 seasons, 5 gameweeks each for 1 player
    for s in ["2022-23", "2023-24"]:
        for gw in range(1, 6):
            rows.append({
                "season": s,
                "gameweek": gw,
                "player_id": 1,
                "total_points": gw * 2,
                "minutes": 90,
                "goals_scored": 1 if gw % 2 == 1 else 0,
            })
    return pd.DataFrame(rows)


def test_pre_deadline_history_excludes_current_and_future_gw():
    df = _make_mock_history()
    # At GW 3 of 2023-24, only 2022-23 (all GWs) and 2023-24 GW 1 and 2 are visible
    filtered = get_pre_deadline_history(df, current_season="2023-24", current_gameweek=3)

    # Must contain 5 rows from 2022-23 and 2 rows from 2023-24
    assert len(filtered) == 7
    curr_season_gws = filtered[filtered["season"] == "2023-24"]["gameweek"].tolist()
    assert curr_season_gws == [1, 2]
    assert 3 not in curr_season_gws
    assert 4 not in curr_season_gws


def test_compute_leakage_safe_lags_shift():
    df = _make_mock_history()
    res = compute_leakage_safe_lags(
        df, stat_cols=["total_points"], lags=[1, 2], rolling_windows=[3]
    )

    # For season 2023-24, GW 1: lag_1 should be NaN (start of season)
    p_gw1 = res[(res["season"] == "2023-24") & (res["gameweek"] == 1)].iloc[0]
    assert pd.isna(p_gw1["total_points_lag_1"])

    # For GW 2: total_points was 4 at GW2, but total_points_lag_1 must be 2 (from GW 1)
    p_gw2 = res[(res["season"] == "2023-24") & (res["gameweek"] == 2)].iloc[0]
    assert p_gw2["total_points"] == 4
    assert p_gw2["total_points_lag_1"] == 2

    # For GW 3: total_points was 6, total_points_lag_1 is 4, lag_2 is 2
    p_gw3 = res[(res["season"] == "2023-24") & (res["gameweek"] == 3)].iloc[0]
    assert p_gw3["total_points"] == 6
    assert p_gw3["total_points_lag_1"] == 4
    assert p_gw3["total_points_lag_2"] == 2

    # Rolling 3 mean for GW 3 should be mean of [GW1, GW2] -> (2 + 4) / 2 = 3.0
    assert p_gw3["total_points_roll_3_mean"] == pytest.approx(3.0)


def test_reject_zero_lag():
    df = _make_mock_history()
    with pytest.raises(ValueError, match="All lags must be >= 1"):
        compute_leakage_safe_lags(df, stat_cols=["total_points"], lags=[0, 1])


def test_verify_no_future_leakage_catches_future_rows():
    bad_features = pd.DataFrame([
        {"season": "2023-24", "gameweek": 2, "player_id": 1, "feat": 10},
        {"season": "2023-24", "gameweek": 5, "player_id": 1, "feat": 12},  # future!
    ])
    with pytest.raises(ValueError, match="Temporal leakage detected"):
        verify_no_future_leakage(bad_features, target_season="2023-24", target_gameweek=3)


def test_verify_no_future_leakage_catches_target_gw_raw_outcomes():
    bad_features = pd.DataFrame([
        {"season": "2023-24", "gameweek": 3, "player_id": 1, "total_points": 10, "minutes": 90},
    ])
    with pytest.raises(ValueError, match="Target gameweek outcome leakage detected"):
        verify_no_future_leakage(bad_features, target_season="2023-24", target_gameweek=3)


def test_verify_no_future_leakage_allows_exempted_target():
    # In training, total_points may be present as the target label y
    features = pd.DataFrame([
        {
            "season": "2023-24",
            "gameweek": 3,
            "player_id": 1,
            "total_points": 10,
            "total_points_lag_1": 6.0,
        },
    ])
    # Should succeed with exemption
    verify_no_future_leakage(
        features,
        target_season="2023-24",
        target_gameweek=3,
        allowed_target_cols=["total_points"],
    )

    # But still reject if an un-exempted outcome column like minutes is present
    features_with_minutes = features.assign(minutes=90)
    with pytest.raises(ValueError, match="Target gameweek outcome leakage detected"):
        verify_no_future_leakage(
            features_with_minutes,
            target_season="2023-24",
            target_gameweek=3,
            allowed_target_cols=["total_points"],
        )


def test_verify_no_future_leakage_passes_on_pure_lag_features():
    clean_features = pd.DataFrame([
        {
            "season": "2023-24",
            "gameweek": 3,
            "player_id": 1,
            "total_points_lag_1": 4.0,
            "minutes_lag_1": 90.0,
            "price": 14.0,
        },
    ])
    # Should pass without error since only lagged metrics and pre-match price are present
    verify_no_future_leakage(clean_features, target_season="2023-24", target_gameweek=3)
