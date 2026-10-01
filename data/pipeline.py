"""Transformation pipelines to convert raw FPL data into clean, validated player-gameweek datasets."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from data.schema import (
    ALL_REQUIRED_COLUMNS,
    PERFORMANCE_COLUMNS,
    POSITION_ID_TO_NAME,
    POSITION_NAME_TO_ID,
    validate_player_gameweek_df,
)
from data.ingestion.fetch import (
    fetch_github_season_merged_gw,
    generate_synthetic_raw_data,
)


def clean_raw_merged_gw(raw_df: pd.DataFrame, season: str) -> pd.DataFrame:
    """Clean and standardize a raw merged_gw DataFrame into the project schema.

    Handles column mapping, price rescaling, position normalization, and DGW aggregation.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Raw merged_gw DataFrame.
    season : str
        Season string identifier (e.g., '2023-24').

    Returns
    -------
    pd.DataFrame
        Standardized, validated player-gameweek DataFrame.
    """
    df = raw_df.copy()

    # Column name mappings
    col_map = {
        "GW": "gameweek",
        "element": "player_id",
        "name": "player_name",
        "xG": "expected_goals",
        "xA": "expected_assists",
        "xGI": "expected_goal_involvements",
        "xGC": "expected_goals_conceded",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Web name
    if "web_name" not in df.columns:
        if "player_name" in df.columns:
            df["web_name"] = df["player_name"].apply(lambda n: str(n).split("_")[-1] if "_" in str(n) else str(n).split()[-1])
        else:
            df["web_name"] = "Unknown"

    # Season
    df["season"] = season

    # Price normalization (in raw data, value is in 0.1m, e.g. 55 -> 5.5)
    if "value" in df.columns and "price" not in df.columns:
        df["price"] = df["value"].astype(float) / 10.0
    elif "price" in df.columns and df["price"].max() > 30.0:
        df["price"] = df["price"].astype(float) / 10.0

    # Position normalization
    if "position" in df.columns:
        # Some datasets have numeric position strings or codes
        def _norm_pos(val: object) -> str:
            if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                return POSITION_ID_TO_NAME.get(int(val), "MID")
            val_str = str(val).upper().strip()
            if val_str in POSITION_NAME_TO_ID:
                return val_str
            return "MID"

        df["position"] = df["position"].apply(_norm_pos)
        df["element_type"] = df["position"].map(POSITION_NAME_TO_ID)
    elif "element_type" in df.columns:
        df["position"] = df["element_type"].map(POSITION_ID_TO_NAME)
    else:
        df["position"] = "MID"
        df["element_type"] = 3

    # Team ID
    if "team_id" not in df.columns:
        if "team" in df.columns:
            # Create deterministic integer team IDs
            teams = sorted(df["team"].dropna().unique().tolist())
            team_map = {t: i + 1 for i, t in enumerate(teams)}
            df["team_id"] = df["team"].map(team_map).fillna(1).astype(int)
        else:
            df["team"] = "Unknown"
            df["team_id"] = 1

    # Opponent Team ID
    if "opponent_team_id" not in df.columns:
        if "opponent_team" in df.columns:
            opponents = sorted(df["opponent_team"].dropna().unique().tolist())
            opp_map = {o: i + 1 for i, o in enumerate(opponents)}
            df["opponent_team_id"] = df["opponent_team"].map(opp_map).fillna(1).astype(int)
        else:
            df["opponent_team"] = "None"
            df["opponent_team_id"] = 0

    # Missing performance columns default to 0
    for col in PERFORMANCE_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    # Ensure matches_in_gw column exists
    if "matches_in_gw" not in df.columns:
        df["matches_in_gw"] = 1

    # Ensure kickoff_time and was_home
    if "kickoff_time" not in df.columns:
        df["kickoff_time"] = "2023-08-12T15:00:00Z"
    if "was_home" not in df.columns:
        df["was_home"] = True

    # Aggregate Double Gameweeks (DGW) where multiple matches occur for the same player in one GW
    group_keys = ["season", "gameweek", "player_id"]
    
    # Aggregation rules
    agg_dict: dict[str, str] = {
        "player_name": "first",
        "web_name": "first",
        "team": "first",
        "team_id": "first",
        "position": "first",
        "element_type": "first",
        "price": "last",  # Price after all matches in the GW
        "opponent_team": lambda s: " & ".join(map(str, s)),
        "opponent_team_id": "first",
        "was_home": "first",
        "kickoff_time": "first",
        "matches_in_gw": "count",
    }
    for col in PERFORMANCE_COLUMNS:
        agg_dict[col] = "sum"

    aggregated = df.groupby(group_keys, as_index=False).agg(agg_dict)

    # Cast types cleanly
    int_cols = ["gameweek", "player_id", "team_id", "element_type", "matches_in_gw"] + [
        "minutes", "total_points", "goals_scored", "assists", "clean_sheets",
        "goals_conceded", "own_goals", "penalties_saved", "penalties_missed",
        "yellow_cards", "red_cards", "saves", "bonus", "bps"
    ]
    for c in int_cols:
        if c in aggregated.columns:
            aggregated[c] = aggregated[c].fillna(0).astype(int)

    float_cols = ["price", "influence", "creativity", "threat", "ict_index",
                  "expected_goals", "expected_assists", "expected_goal_involvements",
                  "expected_goals_conceded"]
    for c in float_cols:
        if c in aggregated.columns:
            aggregated[c] = aggregated[c].fillna(0.0).astype(float)

    # Sort deterministically
    sorted_df = aggregated.sort_values(by=["player_id", "gameweek"]).reset_index(drop=True)

    # Validate against schema
    val = validate_player_gameweek_df(sorted_df)
    if not val.is_valid:
        raise ValueError(f"Schema validation failed on cleaned dataset: {val.error_messages}")

    return sorted_df


def process_and_save_season(
    season: str,
    raw_dir: Path | str = "data/raw",
    processed_dir: Path | str = "data/processed",
    allow_synthetic: bool = False,
    auto_fetch: bool = True,
) -> Path:
    """Read raw season merged_gw.csv, clean it, and save to data/processed.

    Parameters
    ----------
    season : str
        Season string identifier.
    raw_dir : Path | str
        Path containing raw files.
    processed_dir : Path | str
        Path to save processed files.
    allow_synthetic : bool
        If True and raw file is missing, generates synthetic data for testing.
        Defaults to False to prevent accidental training or evaluation on mock data.
    auto_fetch : bool
        If True and raw file is missing (with allow_synthetic=False), attempts
        to download merged_gw.csv from GitHub. Defaults to True.

    Returns
    -------
    Path
        Path to the saved processed CSV file.

    Raises
    ------
    FileNotFoundError
        If raw file does not exist and allow_synthetic=False and auto-fetch fails or is disabled.
    """
    raw_path = Path(raw_dir) / season / "merged_gw.csv"
    if not raw_path.exists():
        if allow_synthetic:
            generate_synthetic_raw_data(season=season, raw_base_dir=raw_dir)
        elif auto_fetch:
            try:
                fetch_github_season_merged_gw(season=season, raw_base_dir=raw_dir)
            except Exception as exc:
                raise FileNotFoundError(
                    f"Raw data file not found at {raw_path} and auto-fetch from GitHub failed: {exc}. "
                    f"For testing with synthetic data, pass allow_synthetic=True explicitly."
                ) from exc
        else:
            raise FileNotFoundError(
                f"Raw data file not found at {raw_path}. Run fetch_github_season_merged_gw('{season}') "
                f"or set allow_synthetic=True for testing."
            )

    raw_df = pd.read_csv(raw_path)
    clean_df = clean_raw_merged_gw(raw_df, season=season)

    out_dir = Path(processed_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"players_gw_{season}.csv"
    clean_df.to_csv(out_path, index=False)
    return out_path


def load_clean_player_gw_data(
    season: str,
    processed_dir: Path | str = "data/processed",
    raw_dir: Path | str = "data/raw",
    allow_synthetic: bool = False,
    auto_fetch: bool = True,
) -> pd.DataFrame:
    """Load cleaned player-gameweek dataset, processing from raw if needed.

    Parameters
    ----------
    season : str
        Season string identifier.
    processed_dir : Path | str
        Path to processed directory.
    raw_dir : Path | str
        Path to raw directory.
    allow_synthetic : bool
        If True and raw data is missing, permits synthetic generation.
        Defaults to False to protect downstream models from synthetic data.
    auto_fetch : bool
        If True and raw data is missing, attempts to fetch from GitHub.
        Defaults to True.

    Returns
    -------
    pd.DataFrame
        Clean, validated DataFrame.

    Raises
    ------
    FileNotFoundError
        If raw or processed data is unavailable and allow_synthetic=False.
    """
    proc_path = Path(processed_dir) / f"players_gw_{season}.csv"
    if not proc_path.exists():
        process_and_save_season(
            season=season,
            raw_dir=raw_dir,
            processed_dir=processed_dir,
            allow_synthetic=allow_synthetic,
            auto_fetch=auto_fetch,
        )

    return pd.read_csv(proc_path)


def load_synthetic_player_gw_data(
    season: str = "2023-24",
    processed_dir: Path | str = "data/processed",
    raw_dir: Path | str = "data/raw",
    num_players: int = 40,
    num_gws: int = 38,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate and load synthetic player-gameweek data explicitly for testing/benchmarks.

    Synthetic data is explicitly opt-in and does not masquerade as real data without intention.
    """
    generate_synthetic_raw_data(
        season=season,
        raw_base_dir=raw_dir,
        num_players=num_players,
        num_gws=num_gws,
        seed=seed,
    )
    process_and_save_season(
        season=season,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        allow_synthetic=True,
    )
    return pd.read_csv(Path(processed_dir) / f"players_gw_{season}.csv")
