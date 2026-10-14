"""Backtest evaluation metrics for NextGW.

Owner: print-tanish (Tanishq). This module scores the historical simulator
(``backtesting/simulator.py``, TA619) and the baselines (``baselines/``) so the
planner, the greedy 1-GW strategy and the rule-based strategy can be compared
on identical terms.

The simulator output contract is NOT yet documented (see the PROPOSED section
below); the exact question for TA619 is recorded in
``mimi/state/print-tanish.md``.

=====================================================================
EVALUATION PLAN
=====================================================================

CONFIRMED requirements (README.md "Evaluation", AGENTS.md):
- Primary metric: cumulative FPL points over the backtest period.
- Secondary metrics: points per Gameweek, transfer hits, captain points, chip
  contribution, decision stability, runtime.
- Transfer hits cost 4 points each (official FPL rule) and MUST stay
  configurable, never hard-coded deep in logic (TarunPK15, README references).
- No leakage: a simulated decision for Gameweek t may use only information
  available before the Gameweek t deadline (AGENTS.md section 5).
- Prediction quality (MAE / RMSE) is reported separately by
  ``prediction/evaluate.py`` and is NOT a planning metric here.
- Every experiment records its data period, features and config next to its
  output (AGENTS.md section 5).

PROPOSED (not yet agreed with any owner):
- The exact shape of one simulated Gameweek record that metrics consumes.
  Nothing on ``main`` documents it: ``backtesting/simulator.py`` and
  ``backtesting/experiments.py`` are empty. The question is raised with TA619
  and recorded in ``mimi/state/print-tanish.md``.
- The reporting output shape (per-strategy summary vs per-Gameweek table).

CANDIDATE METRICS AND DEFINITIONS:
- cumulative_points: sum of net points across the backtest Gameweeks.
- points_per_gameweek: cumulative_points divided by the number of Gameweeks.
- transfer_hit_points: max(0, transfers - free_transfers) * cost_per_hit.
- captain_points: points scored by the captain beyond the same player's
  non-captain contribution (the double).
- chip_contribution: points earned under a chip minus the points the same XI
  would have scored without it.
- decision_stability: how often the recommended plan changes between
  consecutive Gameweeks (fewer changes = more stable).
- runtime: wall-clock seconds to produce each Gameweek's decision.

REQUIRED INPUTS (per Gameweek, minimum): starting XI player ids, captain id,
vice-captain id, number of transfers, free transfers available, chip activated
or none, and the actual per-player points. None of these has a documented
shape yet.

EDGE CASES: blank Gameweek (0 matches, ``matches_in_gw == 0``), double Gameweek
(2 matches), no captain selected, chips (Wildcard, Free Hit, Bench Boost,
Triple Captain where the captain scores x3), zero-minute players, a player with
no row in the Gameweek, and an empty backtest window.

PROPOSED TESTS live in ``tests/test_metrics_*.py``.

EXPERIMENT COMPARISONS (README.md): proposed planner vs greedy 1-GW vs
rule-based baseline; ablations over planning horizon (1 vs 2 vs 4 GW),
deterministic vs scenario-based uncertainty, search budget, and baseline vs ML
predictor.

=====================================================================
IMPLEMENTATION SCOPE
=====================================================================
The functions below are schema-independent numeric primitives. They take plain
per-Gameweek numbers, so they depend on no teammate's DataFrame or dataclass
shape and do NOT define the simulator contract. Composition with the simulator
is deferred until the output contract is agreed with TA619.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "cumulative_points",
    "points_per_gameweek",
    "transfer_hit_points",
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
