"""Tests for data/schema.py: column completeness, validation, and types."""

import pandas as pd
import pytest

from data.schema import (
    ALL_REQUIRED_COLUMNS,
    IDENTIFIER_COLUMNS,
    METADATA_COLUMNS,
    PERFORMANCE_COLUMNS,
    POSITION_ID_TO_NAME,
    POSITION_NAME_TO_ID,
    validate_player_gameweek_df,
)


def _make_valid_sample_df() -> pd.DataFrame:
    """Helper creating a minimal valid player-gameweek row."""
    row = {
        "season": "2023-24",
        "gameweek": 1,
        "player_id": 101,
        "player_name": "Erling Haaland",
        "web_name": "Haaland",
        "team": "Man City",
        "team_id": 11,
        "position": "FWD",
        "element_type": 4,
        "price": 14.0,
        "opponent_team": "Burnley",
        "opponent_team_id": 5,
        "was_home": False,
        "kickoff_time": "2023-08-11T19:00:00Z",
        "matches_in_gw": 1,
        "minutes": 80,
        "total_points": 13,
        "goals_scored": 2,
        "assists": 0,
        "clean_sheets": 0,
        "goals_conceded": 0,
        "own_goals": 0,
        "penalties_saved": 0,
        "penalties_missed": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "saves": 0,
        "bonus": 3,
        "bps": 40,
        "influence": 70.0,
        "creativity": 10.0,
        "threat": 65.0,
        "ict_index": 14.5,
        "expected_goals": 1.8,
        "expected_assists": 0.1,
        "expected_goal_involvements": 1.9,
        "expected_goals_conceded": 0.2,
    }
    return pd.DataFrame([row])


def test_schema_valid_df():
    df = _make_valid_sample_df()
    res = validate_player_gameweek_df(df)
    assert res.is_valid
    assert len(res.missing_columns) == 0
    assert len(res.error_messages) == 0


def test_schema_missing_column():
    df = _make_valid_sample_df().drop(columns=["total_points"])
    res = validate_player_gameweek_df(df)
    assert not res.is_valid
    assert "total_points" in res.missing_columns


def test_schema_invalid_position():
    df = _make_valid_sample_df()
    df.loc[0, "position"] = "GOALKEEPER"  # Should be GK
    res = validate_player_gameweek_df(df)
    assert not res.is_valid
    assert "GOALKEEPER" in res.invalid_positions


def test_schema_invalid_gameweek():
    df = _make_valid_sample_df()
    df.loc[0, "gameweek"] = 40  # GW must be 1-38
    res = validate_player_gameweek_df(df)
    assert not res.is_valid
    assert any("Gameweek values must be within" in msg for msg in res.error_messages)


def test_schema_negative_price():
    df = _make_valid_sample_df()
    df.loc[0, "price"] = -1.5
    res = validate_player_gameweek_df(df)
    assert not res.is_valid
    assert any("Price values cannot be negative" in msg for msg in res.error_messages)


def test_position_mappings_bidirectional():
    for pid, name in POSITION_ID_TO_NAME.items():
        assert POSITION_NAME_TO_ID[name] == pid
