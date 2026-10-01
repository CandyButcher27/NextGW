"""Leakage prevention, verification utilities, and temporal feature safeguards.

Rule from AGENTS.md:
"No leakage: a feature or simulated decision for Gameweek t may only use
information available before the Gameweek t deadline. No later outcomes,
prices, transfers or injury news."
"""

from __future__ import annotations

import pandas as pd
from data.schema import PERFORMANCE_COLUMNS


def get_pre_deadline_history(
    df: pd.DataFrame,
    current_season: str,
    current_gameweek: int,
) -> pd.DataFrame:
    """Return historical player records strictly available before `current_gameweek` deadline.

    Any match outcomes occurring in `current_gameweek` or later are strictly excluded.
    Prior seasons are fully included. In `current_season`, only gameweeks < `current_gameweek`
    are included.

    Parameters
    ----------
    df : pd.DataFrame
        Historical player-gameweek dataset.
    current_season : str
        The season of the upcoming decision (e.g., '2023-24').
    current_gameweek : int
        The gameweek about to be played (1-38).

    Returns
    -------
    pd.DataFrame
        Subset of df containing only information from before the deadline.
    """
    if df.empty:
        return df.copy()

    # Prior seasons are valid historical data
    # In current season, strictly prior gameweeks
    is_prior_season = df["season"] < current_season
    is_prior_gw_same_season = (df["season"] == current_season) & (df["gameweek"] < current_gameweek)

    filtered = df[is_prior_season | is_prior_gw_same_season].copy()
    return filtered


def verify_no_future_leakage(
    feature_df: pd.DataFrame,
    target_season: str,
    target_gameweek: int,
    forbidden_outcome_cols: list[str] | None = None,
    allowed_target_cols: list[str] | None = None,
) -> None:
    """Verify that a feature table for predicting a gameweek does not contain unshifted outcomes.

    Parameters
    ----------
    feature_df : pd.DataFrame
        Features prepared for target_gameweek.
    target_season : str
        Target season being predicted.
    target_gameweek : int
        Target gameweek being predicted.
    forbidden_outcome_cols : list[str] | None
        List of column names representing match outcomes that cannot be present as features.
        Defaults to PERFORMANCE_COLUMNS.
    allowed_target_cols : list[str] | None
        Optional list of outcome columns explicitly permitted as prediction targets (e.g. ['total_points']).

    Raises
    ------
    ValueError
        If unshifted outcome columns are present for the target gameweek or future gameweek data is detected.
    """
    if feature_df.empty:
        return

    cols_to_check = forbidden_outcome_cols if forbidden_outcome_cols is not None else PERFORMANCE_COLUMNS
    allowed = set(allowed_target_cols or [])

    # Check for any row in feature_df that has gameweek > target_gameweek in target_season
    future_rows = (feature_df["season"] == target_season) & (feature_df["gameweek"] > target_gameweek)
    if future_rows.any():
        n_bad = int(future_rows.sum())
        raise ValueError(
            f"Temporal leakage detected: feature table contains {n_bad} rows "
            f"from future gameweeks (> {target_gameweek}) in season {target_season}."
        )

    # Check if target gameweek rows directly contain unshifted match outcome columns
    target_rows = (feature_df["season"] == target_season) & (feature_df["gameweek"] == target_gameweek)
    if target_rows.any():
        leaked_cols = [
            col for col in cols_to_check
            if col in feature_df.columns and col not in allowed
        ]
        if leaked_cols:
            raise ValueError(
                f"Target gameweek outcome leakage detected: feature table contains unshifted "
                f"outcome columns {leaked_cols} for target gameweek {target_gameweek} in season {target_season}."
            )


def compute_leakage_safe_lags(
    df: pd.DataFrame,
    stat_cols: list[str],
    lags: list[int] = [1, 2, 3],
    rolling_windows: list[int] = [3, 5],
) -> pd.DataFrame:
    """Compute historical lag and rolling average features strictly shifted by >= 1 gameweek.

    For Gameweek t, lag 1 is the value at t - 1. A rolling average of window w
    is the mean of [t - w, ..., t - 1]. The outcome at Gameweek t is NEVER included.

    Parameters
    ----------
    df : pd.DataFrame
        Clean player-gameweek DataFrame.
    stat_cols : list[str]
        Metrics to lag (e.g. ['total_points', 'minutes', 'goals_scored', 'assists']).
    lags : list[int]
        Lag steps to compute. Each lag must be >= 1.
    rolling_windows : list[int]
        Window sizes for rolling means.

    Returns
    -------
    pd.DataFrame
        DataFrame with added lag and rolling columns, preserving all original columns.
    """
    if any(lag < 1 for lag in lags):
        raise ValueError("All lags must be >= 1 to prevent target gameweek outcome leakage.")

    # Sort deterministically by player, season, and gameweek
    result = df.sort_values(by=["player_id", "season", "gameweek"]).copy()

    for col in stat_cols:
        if col not in result.columns:
            continue

        grouped = result.groupby(["player_id", "season"])[col]

        # Shifted lags
        for lag in lags:
            col_name = f"{col}_lag_{lag}"
            result[col_name] = grouped.shift(lag)

        # Rolling averages strictly shifted by 1 first
        for w in rolling_windows:
            col_name = f"{col}_roll_{w}_mean"
            # shift(1) ensures the current gameweek t is not included in the window
            result[col_name] = grouped.transform(
                lambda s: s.shift(1).rolling(window=w, min_periods=1).mean()
            )

    return result
