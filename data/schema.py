"""Data schemas, column constants, and validation for player-gameweek datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

# Mapping between numeric element_type and standard position string
POSITION_ID_TO_NAME: dict[int, str] = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD",
}

POSITION_NAME_TO_ID: dict[str, int] = {
    "GK": 1,
    "DEF": 2,
    "MID": 3,
    "FWD": 4,
}

# Standard core columns for clean player-gameweek datasets
IDENTIFIER_COLUMNS: list[str] = [
    "season",
    "gameweek",
    "player_id",
    "player_name",
    "web_name",
]

METADATA_COLUMNS: list[str] = [
    "team",
    "team_id",
    "position",
    "element_type",
    "price",  # Current price in £ millions (e.g., 14.0)
]

FIXTURE_COLUMNS: list[str] = [
    "opponent_team",
    "opponent_team_id",
    "was_home",
    "kickoff_time",
    "matches_in_gw",  # 0 for BGW, 1 for normal, 2 for DGW
]

PERFORMANCE_COLUMNS: list[str] = [
    "minutes",
    "total_points",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
]

PRE_DEADLINE_COLUMNS: list[str] = [
    "status",  # 'a', 'd', 'i', 's', 'u'
    "chance_of_playing_this_round",  # Optional 0.0 - 1.0 or None
    "transfers_in_event",
    "transfers_out_event",
]

ALL_REQUIRED_COLUMNS: list[str] = (
    IDENTIFIER_COLUMNS
    + METADATA_COLUMNS
    + FIXTURE_COLUMNS
    + PERFORMANCE_COLUMNS
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of dataset schema validation."""

    is_valid: bool
    missing_columns: list[str]
    invalid_positions: list[str]
    null_counts: dict[str, int]
    error_messages: list[str]


def validate_player_gameweek_df(df: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame conforms to the clean player-gameweek schema.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate.

    Returns
    -------
    ValidationResult
        Details of validation status, missing columns, or violations.
    """
    errors: list[str] = []

    # Check required columns
    missing = [col for col in ALL_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")

    # Check positions
    invalid_positions: list[str] = []
    if "position" in df.columns:
        valid_pos = set(POSITION_NAME_TO_ID.keys())
        found_pos = set(df["position"].dropna().unique())
        invalid_pos = found_pos - valid_pos
        if invalid_pos:
            invalid_positions = sorted(list(invalid_pos))
            errors.append(f"Invalid positions found: {invalid_positions}")

    # Check gameweek range (1 to 38)
    if "gameweek" in df.columns and not df.empty:
        if (df["gameweek"] < 1).any() or (df["gameweek"] > 38).any():
            errors.append("Gameweek values must be within 1 and 38 inclusive.")

    # Check price is non-negative
    if "price" in df.columns and not df.empty:
        if (df["price"] < 0).any():
            errors.append("Price values cannot be negative.")

    # Check non-null identifier keys
    null_counts: dict[str, int] = {}
    for col in IDENTIFIER_COLUMNS:
        if col in df.columns:
            n_nulls = int(df[col].isna().sum())
            if n_nulls > 0:
                null_counts[col] = n_nulls
                errors.append(f"Identifier column '{col}' has {n_nulls} null values.")

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        missing_columns=missing,
        invalid_positions=invalid_positions,
        null_counts=null_counts,
        error_messages=errors,
    )
