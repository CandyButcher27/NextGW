"""Shared helpers for baseline strategies and backtest transition.

These utilities are imported by both :mod:`baselines.conventional` and
:mod:`baselines.greedy` (via :mod:`planning.strategy`) as well as the
backtest experiment runner in :mod:`scripts.run_backtest`.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from data.leakage import get_pre_deadline_history
from fpl.squad import Player
from fpl.transfers import transition_fn
from planning.actions import GWPlan
from planning.state import PlanningState


def player_registry(history: pd.DataFrame, season: str) -> dict[str, Player]:
    """Build a mapping of player_id -> Player from the most-recent row per player.

    Uses the last gameweek row available in *history* for each player so that
    price, team and position reflect the latest known values before a deadline.

    Args:
        history: Pre-deadline player-gameweek DataFrame (leakage-safe).
        season: Season string, e.g. ``"2024-25"``.

    Returns:
        Dict mapping string player_id to :class:`~fpl.squad.Player`.
    """
    rows = history.loc[history["season"] == season].sort_values("gameweek")
    latest = rows.groupby("player_id").tail(1)
    return {
        str(r.player_id): Player(str(r.player_id), str(r.web_name), str(r.position), str(r.team), float(r.price))
        for r in latest.itertuples()
    }


def active_pool(history: pd.DataFrame, season: str, registry: dict[str, Player]) -> list[Player]:
    """Return players who appeared in the most recent Gameweek of *history*.

    A player who was absent from the last Gameweek (injured, benched by their
    real-world club, or simply not registered yet) is excluded from the pool
    so that the strategies never consider unavailable players as transfer targets.

    Args:
        history: Pre-deadline player-gameweek DataFrame (leakage-safe).
        season: Season string, e.g. ``"2024-25"``.
        registry: Player metadata mapping from :func:`player_registry`.

    Returns:
        List of :class:`~fpl.squad.Player` objects present in the last GW.
    """
    rows = history.loc[history["season"] == season]
    if rows.empty:
        return []
    last_gw = rows["gameweek"].max()
    active = rows.loc[rows["gameweek"] == last_gw, "player_id"].astype(str).unique()
    return [registry[pid] for pid in active]


def backtest_transition(
    data: pd.DataFrame, season: str
) -> Callable[[PlanningState, GWPlan], PlanningState]:
    """Return a transition function that advances state using leakage-safe history.

    The returned callable is used as the ``transition_fn`` argument to
    :func:`~backtesting.simulator.simulate`.  At each Gameweek it rebuilds the
    player registry from information available *before* that Gameweek's deadline,
    ensuring no future prices or availability data leak into the state transition.

    Args:
        data: Full player-gameweek dataset for the season.
        season: Season string, e.g. ``"2024-25"``.

    Returns:
        A ``(state, plan) -> PlanningState`` callable suitable for the simulator.
    """
    def step(state: PlanningState, plan: GWPlan) -> PlanningState:
        history = get_pre_deadline_history(data, current_season=season, current_gameweek=state.gameweek)
        return transition_fn(state, plan, player_registry=player_registry(history, season))

    return step


def recent_minutes(history: pd.DataFrame, season: str, window: int) -> dict[str, float]:
    """Sum each player's minutes over the last *window* Gameweeks in *history*.

    Used by :class:`~baselines.conventional.ConventionalStrategy` to detect
    absent players: a player whose summed minutes is 0 over the recent window
    is treated as unavailable and considered for replacement.

    Args:
        history: Pre-deadline player-gameweek DataFrame (leakage-safe).
        season: Season string, e.g. ``"2024-25"``.
        window: Number of most-recent Gameweeks to include.

    Returns:
        Dict mapping string player_id to total minutes in the window.
    """
    rows = history.loc[history["season"] == season]
    last_gws = sorted(rows["gameweek"].unique())[-window:]
    recent = rows.loc[rows["gameweek"].isin(last_gws)]
    return {str(pid): float(m) for pid, m in recent.groupby("player_id")["minutes"].sum().items()}


def squad_ids(squad: tuple) -> list[str]:
    """Extract string player IDs from a planning squad tuple.

    A planning squad is stored as a tuple of ``(player_id, position)`` pairs
    or bare player-id strings.  This helper normalises both forms.

    Args:
        squad: Sequence of ``(player_id, position)`` pairs or bare id strings.

    Returns:
        List of string player IDs.
    """
    return [str(item[0]) if isinstance(item, (tuple, list)) else str(item) for item in squad]
