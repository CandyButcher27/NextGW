"""Raw data ingestion and fetching pipelines for FPL data.

Fetches historical season data from the open Fantasy-Premier-League repository,
the official FPL API, or generates deterministic synthetic data for offline/test environments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import requests

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
)
FPL_API_BASE = "https://fantasy.premierleague.com/api"


def get_raw_season_dir(season: str, raw_base_dir: Path | str = "data/raw") -> Path:
    """Return the deterministic path for raw season data."""
    base = Path(raw_base_dir)
    return base / season


def fetch_live_bootstrap(timeout: int = 10) -> dict[str, Any]:
    """Fetch current live data from the official FPL bootstrap-static endpoint."""
    url = f"{FPL_API_BASE}/bootstrap-static/"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_live_fixtures(timeout: int = 10) -> list[dict[str, Any]]:
    """Fetch all fixtures from the official FPL API fixtures endpoint."""
    url = f"{FPL_API_BASE}/fixtures/"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_github_season_merged_gw(
    season: str,
    raw_base_dir: Path | str = "data/raw",
    use_cache: bool = True,
    timeout: int = 15,
) -> Path:
    """Fetch the merged_gw.csv file for a given historical season from GitHub.

    Parameters
    ----------
    season : str
        Season string, e.g. '2023-24' or '2022-23'.
    raw_base_dir : Path | str
        Destination directory.
    use_cache : bool
        If True and file exists, skips downloading.
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    Path
        Path to the saved merged_gw.csv file.
    """
    dest_dir = get_raw_season_dir(season, raw_base_dir)
    dest_file = dest_dir / "merged_gw.csv"

    if use_cache and dest_file.exists():
        return dest_file

    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"{GITHUB_RAW_BASE}/{season}/gws/merged_gw.csv"

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    dest_file.write_bytes(resp.content)
    return dest_file


def generate_synthetic_raw_data(
    season: str = "2023-24",
    raw_base_dir: Path | str = "data/raw",
    num_players: int = 40,
    num_gws: int = 38,
    seed: int = 42,
) -> Path:
    """Generate realistic, deterministic synthetic raw FPL data for testing and offline runs.

    Parameters
    ----------
    season : str
        Season label.
    raw_base_dir : Path | str
        Directory to write raw files.
    num_players : int
        Number of players in the mock league.
    num_gws : int
        Number of gameweeks to simulate.
    seed : int
        Random seed for full reproducibility.

    Returns
    -------
    Path
        Path to the generated merged_gw.csv file.
    """
    rng = np.random.default_rng(seed)
    dest_dir = get_raw_season_dir(season, raw_base_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    teams = [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
        "Man City", "Man Utd", "Newcastle", "Nott'm Forest", "Spurs",
        "West Ham", "Wolves", "Luton", "Burnley", "Sheffield Utd"
    ]
    positions = ["GK", "DEF", "MID", "FWD"]
    pos_weights = [0.12, 0.35, 0.38, 0.15]

    players = []
    for pid in range(1, num_players + 1):
        pos = rng.choice(positions, p=pos_weights)
        team = rng.choice(teams)
        base_price = int(rng.uniform(45, 135))  # in 0.1m, e.g. 45 = 4.5m
        players.append({
            "element": pid,
            "name": f"Player_{pid}",
            "position": pos,
            "team": team,
            "base_price": base_price,
        })

    records = []
    for gw in range(1, num_gws + 1):
        for p in players:
            # Chance of player playing minutes
            plays = rng.random() > 0.15
            minutes = int(rng.choice([90, 85, 70, 60, 45, 30, 15])) if plays else 0

            # Generate stats depending on position and minutes
            goals = int(rng.poisson(0.4 if p["position"] in ["MID", "FWD"] else 0.05)) if minutes > 0 else 0
            assists = int(rng.poisson(0.3 if p["position"] in ["MID", "FWD"] else 0.1)) if minutes > 0 else 0
            clean_sheet = int(rng.random() > 0.65) if (minutes >= 60 and p["position"] in ["GK", "DEF"]) else 0
            goals_conceded = int(rng.poisson(1.2)) if minutes > 0 else 0
            saves = int(rng.poisson(3.5)) if (p["position"] == "GK" and minutes > 0) else 0
            yellow = int(rng.random() < 0.15) if minutes > 0 else 0
            red = int(rng.random() < 0.02) if minutes > 0 else 0
            bonus = int(rng.choice([0, 1, 2, 3], p=[0.75, 0.1, 0.1, 0.05])) if minutes > 0 else 0

            # Points calculation
            pts = 0
            if minutes > 0:
                pts += 1 if minutes < 60 else 2
            if p["position"] == "FWD":
                pts += goals * 4
            elif p["position"] == "MID":
                pts += goals * 5 + clean_sheet * 1
            else:  # GK, DEF
                pts += goals * 6 + clean_sheet * 4 - (goals_conceded // 2)
            pts += assists * 3 + (saves // 3) + bonus - yellow - (red * 3)

            opp_team = rng.choice([t for t in teams if t != p["team"]])
            was_home = bool(rng.random() > 0.5)
            value = p["base_price"] + rng.integers(-3, 4)

            records.append({
                "name": p["name"],
                "element": p["element"],
                "position": p["position"],
                "team": p["team"],
                "GW": gw,
                "opponent_team": opp_team,
                "was_home": was_home,
                "kickoff_time": f"2023-08-12T15:00:00Z",
                "value": max(38, value),
                "total_points": pts,
                "minutes": minutes,
                "goals_scored": goals,
                "assists": assists,
                "clean_sheets": clean_sheet,
                "goals_conceded": goals_conceded,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": yellow,
                "red_cards": red,
                "saves": saves,
                "bonus": bonus,
                "bps": int(pts * 4 + rng.integers(0, 10)),
                "influence": round(float(pts * 5.2 + rng.uniform(0, 10)), 1),
                "creativity": round(float(assists * 25.0 + rng.uniform(0, 15)), 1),
                "threat": round(float(goals * 35.0 + rng.uniform(0, 20)), 1),
                "ict_index": round(float(pts * 1.5 + rng.uniform(0, 5)), 1),
                "xG": round(float(goals * 0.8 + rng.uniform(0, 0.3)), 2),
                "xA": round(float(assists * 0.7 + rng.uniform(0, 0.2)), 2),
                "xGI": round(float((goals + assists) * 0.75 + rng.uniform(0, 0.3)), 2),
                "xGC": round(float(goals_conceded * 0.9 + rng.uniform(0, 0.5)), 2),
            })

    df = pd.DataFrame(records)
    merged_path = dest_dir / "merged_gw.csv"
    df.to_csv(merged_path, index=False)
    return merged_path
