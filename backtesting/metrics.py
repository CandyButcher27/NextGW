"""Backtest evaluation metrics for NextGW.

Scalar primitives take plain per-Gameweek numbers. ``summarize`` takes the simulator's
``RESULT_COLUMNS`` frame (DEC-TA-1) and reports, per strategy: total and per-GW points,
transfers and hits, captain bonus, decision stability (starting-XI players changed per GW)
and decision runtime.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

__all__ = [
    "cumulative_points",
    "points_per_gameweek",
    "summarize",
    "transfer_hit_points",
    "xi_changes",
]

DEFAULT_TRANSFER_HIT_COST = 4


def cumulative_points(gw_points: Sequence[float]) -> float:
    """Return the sum of net points across the backtest Gameweeks.

    Parameters
    ----------
    gw_points : Sequence[float]
        Net points for each Gameweek, already net of transfer hits and chip
        costs if the caller accounts for them. An empty sequence yields 0.0.

    Returns
    -------
    float
        Cumulative points.
    """
    return float(sum(float(points) for points in gw_points))


def points_per_gameweek(gw_points: Sequence[float]) -> float:
    """Return the mean net points per backtest Gameweek.

    Parameters
    ----------
    gw_points : Sequence[float]
        Net points for each Gameweek.

    Returns
    -------
    float
        Mean points per Gameweek.

    Raises
    ------
    ValueError
        If ``gw_points`` is empty, since the mean is undefined.
    """
    values = [float(points) for points in gw_points]
    if not values:
        raise ValueError("points_per_gameweek requires at least one Gameweek")
    return sum(values) / len(values)


def transfer_hit_points(
    num_transfers: int,
    free_transfers: int,
    *,
    cost_per_hit: int = DEFAULT_TRANSFER_HIT_COST,
) -> int:
    """Return the points deducted for transfer hits in one Gameweek.

    A hit is charged for each transfer beyond the free transfers available.
    The default cost is 4, the official FPL rule, and stays configurable.

    Parameters
    ----------
    num_transfers : int
        Total transfers made in the Gameweek.
    free_transfers : int
        Free transfers available before the Gameweek.
    cost_per_hit : int, optional
        Points deducted per transfer beyond the free transfers. Default 4.

    Returns
    -------
    int
        Total points deducted (0 when no hit is taken).

    Raises
    ------
    ValueError
        If any argument is negative.
    """
    if num_transfers < 0 or free_transfers < 0 or cost_per_hit < 0:
        raise ValueError("num_transfers, free_transfers and cost_per_hit must be non-negative")
    hits = max(0, num_transfers - free_transfers)
    return hits * cost_per_hit


def xi_changes(starting_xis: Sequence[str]) -> list[int]:
    """Players entering the starting XI at each GW after the first; XIs are comma-joined ids."""
    xis = [set(xi.split(",")) for xi in starting_xis]
    return [len(current - previous) for previous, current in zip(xis, xis[1:])]


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for strategy, runs in results.groupby("strategy"):
        keys = [c for c in ("season", "seed") if c in runs.columns]
        changes = [
            change
            for _, run in (runs.groupby(keys) if keys else [(None, runs)])
            for change in xi_changes(list(run.sort_values("gameweek")["starting_xi"]))
        ]
        runs_count = len(runs.groupby(keys)) if keys else 1
        rows[strategy] = {
            "points_per_run": runs["gw_points"].sum() / runs_count,
            "points_per_gw": points_per_gameweek(list(runs["gw_points"])),
            "transfers_per_run": runs["num_transfers"].sum() / runs_count,
            "hits_per_run": runs["hits"].sum() / runs_count,
            "captain_bonus_per_run": runs["captain_bonus"].sum() / runs_count,
            "xi_changes_per_gw": sum(changes) / len(changes) if changes else 0.0,
            "decision_seconds": runs["decision_seconds"].mean() if "decision_seconds" in runs else float("nan"),
        }
    return pd.DataFrame.from_dict(rows, orient="index").sort_values("points_per_run", ascending=False)
