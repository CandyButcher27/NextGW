from __future__ import annotations

import pandas as pd

from data.leakage import get_pre_deadline_history
from fpl.squad import Player
from fpl.transfers import transition_fn


def player_registry(history: pd.DataFrame, season: str) -> dict[str, Player]:
    rows = history.loc[history["season"] == season].sort_values("gameweek")
    latest = rows.groupby("player_id").tail(1)
    return {
        str(r.player_id): Player(str(r.player_id), str(r.web_name), str(r.position), str(r.team), float(r.price))
        for r in latest.itertuples()
    }


def active_pool(history: pd.DataFrame, season: str, registry: dict[str, Player]) -> list[Player]:
    rows = history.loc[history["season"] == season]
    if rows.empty:
        return []
    last_gw = rows["gameweek"].max()
    active = rows.loc[rows["gameweek"] == last_gw, "player_id"].astype(str).unique()
    return [registry[pid] for pid in active]


def rolling_form(history: pd.DataFrame, season: str, window: int) -> dict[str, float]:
    rows = history.loc[history["season"] == season]
    per_gw = rows.groupby(["player_id", "gameweek"])["total_points"].sum().reset_index()
    recent = per_gw.sort_values("gameweek").groupby("player_id").tail(window)
    return {str(pid): float(pts) for pid, pts in recent.groupby("player_id")["total_points"].mean().items()}


def form_forecast(history: pd.DataFrame, season: str, gameweek: int, horizon: int, window: int = 4) -> dict[int, dict[str, float]]:
    form = rolling_form(history, season, window)
    return {gw: form for gw in range(gameweek, gameweek + horizon)}


def backtest_transition(data: pd.DataFrame, season: str):
    def step(state, plan):
        history = get_pre_deadline_history(data, current_season=season, current_gameweek=state.gameweek)
        return transition_fn(state, plan, player_registry=player_registry(history, season))

    return step


def recent_minutes(history: pd.DataFrame, season: str, window: int) -> dict[str, float]:
    rows = history.loc[history["season"] == season]
    last_gws = sorted(rows["gameweek"].unique())[-window:]
    recent = rows.loc[rows["gameweek"].isin(last_gws)]
    return {str(pid): float(m) for pid, m in recent.groupby("player_id")["minutes"].sum().items()}


def squad_ids(squad) -> list[str]:
    return [str(item[0]) if isinstance(item, (tuple, list)) else str(item) for item in squad]
