"""Leakage-safe feature construction for player Gameweek point forecasts."""

from __future__ import annotations

import pandas as pd

from data.leakage import compute_leakage_safe_lags, verify_no_future_leakage

TARGET_COLUMN = "total_points"
HISTORY_STATS: tuple[str, ...] = (
    "total_points",
    "minutes",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "bonus",
    "bps",
)
LAGS: tuple[int, ...] = (1, 2, 3)
ROLLING_WINDOWS: tuple[int, ...] = (3, 5)
NUMERIC_FEATURES: tuple[str, ...] = (
    "gameweek",
    "was_home",
    "matches_in_gw",
    *(f"{stat}_lag_{lag}" for stat in HISTORY_STATS for lag in LAGS),
    *(f"{stat}_roll_{window}_mean" for stat in HISTORY_STATS for window in ROLLING_WINDOWS),
)
CATEGORICAL_FEATURES: tuple[str, ...] = (
    "position",
    "team",
    "opponent_team",
)
FEATURE_COLUMNS: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
KEY_COLUMNS: tuple[str, ...] = ("season", "gameweek", "player_id")


def build_feature_frame(player_gameweeks: pd.DataFrame) -> pd.DataFrame:
    """Build model inputs without exposing current or future player outcomes.

    The returned table contains identifiers and explicitly selected predictors only.
    Historical statistics are shifted by at least one Gameweek within each player and
    season. Fixture context is limited to schedule fields available before the deadline.
    """
    missing = [column for column in KEY_COLUMNS if column not in player_gameweeks.columns]
    if missing:
        raise ValueError(f"Missing required key columns: {missing}")

    frame = player_gameweeks.copy().reset_index(drop=True)
    for column in HISTORY_STATS:
        if column not in frame.columns:
            frame[column] = pd.NA
    for column in ("was_home", "matches_in_gw", "team", "opponent_team", "position"):
        if column not in frame.columns:
            frame[column] = pd.NA
    if "gameweek" not in frame.columns:
        raise ValueError("Missing required key columns: ['gameweek']")

    lagged = compute_leakage_safe_lags(
        frame,
        stat_cols=list(HISTORY_STATS),
        lags=list(LAGS),
        rolling_windows=list(ROLLING_WINDOWS),
    )
    selected_columns = [*KEY_COLUMNS, *(column for column in FEATURE_COLUMNS if column not in KEY_COLUMNS)]
    features = lagged.loc[:, selected_columns].sort_index().copy()
    home_text = features["was_home"].astype("string").str.lower()
    features["was_home"] = home_text.map(
        {"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0}
    ).fillna(pd.to_numeric(features["was_home"], errors="coerce"))
    features["gameweek"] = pd.to_numeric(features["gameweek"], errors="coerce")
    features["matches_in_gw"] = pd.to_numeric(features["matches_in_gw"], errors="coerce")
    for column in NUMERIC_FEATURES:
        if column not in {"gameweek", "was_home", "matches_in_gw"}:
            features[column] = pd.to_numeric(features[column], errors="coerce")
    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].astype("string")

    forbidden = [TARGET_COLUMN, *HISTORY_STATS, "price", "transfers_in_event", "transfers_out_event"]
    for (season, gameweek), target_features in features.groupby(["season", "gameweek"], sort=False):
        verify_no_future_leakage(
            target_features,
            target_season=str(season),
            target_gameweek=int(gameweek),
            forbidden_outcome_cols=forbidden,
        )
    return features.reset_index(drop=True)
