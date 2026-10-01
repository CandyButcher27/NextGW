"""Tests for data/pipeline.py: end-to-end cleaning, DGW aggregation, and saving."""

from pathlib import Path
import pandas as pd
import pytest

from data.pipeline import (
    clean_raw_merged_gw,
    load_clean_player_gw_data,
    load_synthetic_player_gw_data,
    process_and_save_season,
)
from data.schema import validate_player_gameweek_df
from data.ingestion.fetch import generate_synthetic_raw_data


def test_clean_raw_merged_gw_standardization():
    raw_df = pd.DataFrame([
        {
            "name": "Bukayo_Saka",
            "element": 10,
            "position": "MID",
            "team": "Arsenal",
            "GW": 1,
            "opponent_team": "Nottingham Forest",
            "was_home": True,
            "kickoff_time": "2023-08-12T12:30:00Z",
            "value": 85,  # 8.5m
            "total_points": 10,
            "minutes": 88,
            "goals_scored": 1,
            "assists": 0,
            "clean_sheets": 0,
            "goals_conceded": 1,
            "own_goals": 0,
            "penalties_saved": 0,
            "penalties_missed": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "saves": 0,
            "bonus": 2,
            "bps": 32,
            "influence": 45.0,
            "creativity": 30.0,
            "threat": 40.0,
            "ict_index": 11.5,
            "xG": 0.45,
            "xA": 0.25,
            "xGI": 0.70,
            "xGC": 0.80,
        }
    ])

    clean = clean_raw_merged_gw(raw_df, season="2023-24")

    val = validate_player_gameweek_df(clean)
    assert val.is_valid
    assert clean.loc[0, "price"] == 8.5
    assert clean.loc[0, "gameweek"] == 1
    assert clean.loc[0, "player_id"] == 10
    assert clean.loc[0, "matches_in_gw"] == 1


def test_double_gameweek_aggregation():
    # Player plays 2 fixtures in GW 20
    raw_df = pd.DataFrame([
        {
            "name": "Erling_Haaland",
            "element": 9,
            "position": "FWD",
            "team": "Man City",
            "GW": 20,
            "opponent_team": "Chelsea",
            "was_home": True,
            "kickoff_time": "2023-12-26T15:00:00Z",
            "value": 140,
            "total_points": 8,
            "minutes": 90,
            "goals_scored": 1,
            "assists": 1,
            "clean_sheets": 0,
            "goals_conceded": 1,
            "own_goals": 0,
            "penalties_saved": 0,
            "penalties_missed": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "saves": 0,
            "bonus": 1,
            "bps": 30,
            "influence": 40.0,
            "creativity": 20.0,
            "threat": 50.0,
            "ict_index": 11.0,
            "xG": 0.8,
            "xA": 0.3,
            "xGI": 1.1,
            "xGC": 0.9,
        },
        {
            "name": "Erling_Haaland",
            "element": 9,
            "position": "FWD",
            "team": "Man City",
            "GW": 20,
            "opponent_team": "Brentford",
            "was_home": False,
            "kickoff_time": "2023-12-30T15:00:00Z",
            "value": 141,
            "total_points": 12,
            "minutes": 85,
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
            "bps": 42,
            "influence": 60.0,
            "creativity": 10.0,
            "threat": 70.0,
            "ict_index": 14.0,
            "xG": 1.4,
            "xA": 0.1,
            "xGI": 1.5,
            "xGC": 0.4,
        },
    ])

    clean = clean_raw_merged_gw(raw_df, season="2023-24")

    assert len(clean) == 1
    assert clean.loc[0, "matches_in_gw"] == 2
    assert clean.loc[0, "total_points"] == 20  # 8 + 12
    assert clean.loc[0, "goals_scored"] == 3  # 1 + 2
    assert clean.loc[0, "minutes"] == 175  # 90 + 85
    assert clean.loc[0, "bonus"] == 4  # 1 + 3
    assert clean.loc[0, "opponent_team"] == "Chelsea & Brentford"


def test_end_to_end_pipeline_reproducible(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"

    # Generate synthetic raw data
    generate_synthetic_raw_data(season="2023-24", raw_base_dir=raw_dir, num_players=10, num_gws=5, seed=42)

    # Run processing twice
    p1 = process_and_save_season(season="2023-24", raw_dir=raw_dir, processed_dir=proc_dir)
    df1 = pd.read_csv(p1)

    p2 = process_and_save_season(season="2023-24", raw_dir=raw_dir, processed_dir=proc_dir)
    df2 = pd.read_csv(p2)

    pd.testing.assert_frame_equal(df1, df2)

    # Verify loaded dataset passes schema
    val = validate_player_gameweek_df(df1)
    assert val.is_valid


def test_missing_raw_data_raises_filenotfound(tmp_path: Path):
    empty_raw = tmp_path / "raw"
    empty_proc = tmp_path / "processed"
    with pytest.raises(FileNotFoundError, match="Raw data file not found"):
        process_and_save_season(
            season="2023-24",
            raw_dir=empty_raw,
            processed_dir=empty_proc,
            allow_synthetic=False,
            auto_fetch=False,
        )

    with pytest.raises(FileNotFoundError):
        load_clean_player_gw_data(
            season="2023-24",
            raw_dir=empty_raw,
            processed_dir=empty_proc,
            allow_synthetic=False,
            auto_fetch=False,
        )


def test_missing_raw_data_with_allow_synthetic_opt_in(tmp_path: Path):
    empty_raw = tmp_path / "raw"
    empty_proc = tmp_path / "processed"
    # When explicitly opted in, generates synthetic data
    out_path = process_and_save_season(
        season="2023-24",
        raw_dir=empty_raw,
        processed_dir=empty_proc,
        allow_synthetic=True,
    )
    assert out_path.exists()
    df = pd.read_csv(out_path)
    assert validate_player_gameweek_df(df).is_valid


def test_load_synthetic_player_gw_data_explicit(tmp_path: Path):
    empty_raw = tmp_path / "raw"
    empty_proc = tmp_path / "processed"
    df = load_synthetic_player_gw_data(
        season="2023-24",
        raw_dir=empty_raw,
        processed_dir=empty_proc,
        num_players=8,
        num_gws=3,
        seed=99,
    )
    assert len(df) == 8 * 3
    assert validate_player_gameweek_df(df).is_valid
