from __future__ import annotations

from collections.abc import Callable

import pandas as pd

SCHEDULE_COLUMNS = ["season", "gameweek", "team", "opponent_team", "was_home"]

Forecaster = Callable[[pd.DataFrame, str, int, int], dict[int, dict[str, float]]]


def rolling_form(history: pd.DataFrame, season: str, window: int) -> dict[str, float]:
    rows = history.loc[history["season"] == season]
    per_gw = rows.groupby(["player_id", "gameweek"])["total_points"].sum().reset_index()
    recent = per_gw.sort_values("gameweek").groupby("player_id").tail(window)
    return {str(pid): float(pts) for pid, pts in recent.groupby("player_id")["total_points"].mean().items()}


def form_forecast(history: pd.DataFrame, season: str, gameweek: int, horizon: int, window: int = 4) -> dict[int, dict[str, float]]:
    form = rolling_form(history, season, window)
    return {gw: form for gw in range(gameweek, gameweek + horizon)}


def fixture_schedule(data: pd.DataFrame) -> dict[tuple[str, int], dict[str, list[tuple[str, bool]]]]:
    schedule: dict[tuple[str, int], dict[str, list[tuple[str, bool]]]] = {}
    for row in data[SCHEDULE_COLUMNS].drop_duplicates(["season", "gameweek", "team"]).itertuples(index=False):
        opponents = [(o.strip(), bool(row.was_home)) for o in str(row.opponent_team).split("&")]
        schedule.setdefault((row.season, int(row.gameweek)), {})[row.team] = opponents
    return schedule


def per_match_form(history: pd.DataFrame, season: str, window: int) -> dict[str, float]:
    rows = history.loc[(history["season"] == season) & (history["matches_in_gw"] > 0)]
    recent = rows.sort_values("gameweek").groupby("player_id").tail(window)
    totals = recent.groupby("player_id")[["total_points", "matches_in_gw"]].sum()
    return {str(pid): float(r.total_points / r.matches_in_gw) for pid, r in totals.iterrows()}


def fixture_factors(history: pd.DataFrame, season: str, shrink: float) -> tuple[dict[str, float], dict[bool, float]]:
    rows = history.loc[(history["season"] == season) & (history["matches_in_gw"] == 1) & (history["minutes"] > 0)]
    if rows.empty:
        return {}, {}
    overall = rows["total_points"].mean()
    by_opp = rows.groupby(rows["opponent_team"].astype(str).str.strip())["total_points"].agg(["sum", "count"])
    opponent = ((by_opp["sum"] + shrink * overall) / (by_opp["count"] + shrink) / overall).to_dict()
    home = (rows.groupby(rows["was_home"].astype(bool))["total_points"].mean() / overall).to_dict()
    return opponent, home


def fixture_forecaster(
    schedule: dict[tuple[str, int], dict[str, list[tuple[str, bool]]]],
    window: int = 4,
    shrink: float = 200.0,
) -> Forecaster:
    def forecast(history: pd.DataFrame, season: str, gameweek: int, horizon: int) -> dict[int, dict[str, float]]:
        form = per_match_form(history, season, window)
        latest = history.loc[history["season"] == season].sort_values("gameweek").groupby("player_id").tail(1)
        team_of = dict(zip(latest["player_id"].astype(str), latest["team"]))
        opponent, home = fixture_factors(history, season, shrink)
        forecasts: dict[int, dict[str, float]] = {}
        for gw in range(gameweek, gameweek + horizon):
            fixtures = schedule.get((season, gw), {})
            forecasts[gw] = {
                pid: pts * sum(opponent.get(opp, 1.0) * home.get(at_home, 1.0) for opp, at_home in fixtures.get(team_of.get(pid), []))
                for pid, pts in form.items()
            }
        return forecasts

    return forecast
