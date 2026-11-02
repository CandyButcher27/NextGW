from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from uncertainty.scenarios import ScenarioResult

from .actions import GWPlan
from .state import PlanningState
from .objective import PlanningObjective
from .search import PlanningSearch

if TYPE_CHECKING:
    from fpl.squad import Player


@dataclass(frozen=True)
class PlanningResult:
    """Best plan sequence and its estimated cumulative expected utility."""

    plans: tuple[GWPlan, ...]
    expected_utility: float | None


def _scenario_forecasts(
    scenarios: Sequence[Mapping[int, Mapping[str | int, float]]] | ScenarioResult,
) -> list[dict[int, dict[str, float]]]:
    """Normalize sampled points into one ``{gw: {player_id: points}}`` map per sample."""
    if isinstance(scenarios, ScenarioResult):
        normalized = [dict() for _ in range(scenarios.n_scenarios)]
        for player_id, player_scenario in scenarios.player_scenarios.items():
            if player_scenario.n_scenarios != scenarios.n_scenarios:
                raise ValueError("Player scenario counts do not match ScenarioResult.n_scenarios")
            for gw_index, gameweek in enumerate(player_scenario.gameweeks):
                for scenario_index, points in enumerate(player_scenario.scenarios[:, gw_index]):
                    normalized[scenario_index].setdefault(int(gameweek), {})[
                        str(player_id)
                    ] = float(points)
        return normalized

    normalized = []
    for scenario in scenarios:
        sample: dict[int, dict[str, float]] = {}
        for gameweek, player_points in scenario.items():
            for player_id, points in player_points.items():
                sample.setdefault(int(gameweek), {})[str(player_id)] = float(points)
        normalized.append(sample)
    return normalized


def _mean_forecasts(
    scenarios: Sequence[Mapping[int, Mapping[str, float]]],
) -> dict[int, dict[str, float]]:
    """Return risk-neutral expected points, treating missing sample values as zero."""
    if not scenarios:
        return {}

    totals: dict[int, dict[str, float]] = {}
    for scenario in scenarios:
        for gameweek, player_points in scenario.items():
            gw_totals = totals.setdefault(gameweek, {})
            for player_id, points in player_points.items():
                gw_totals[player_id] = gw_totals.get(player_id, 0.0) + points

    scenario_count = len(scenarios)
    return {
        gameweek: {
            player_id: total / scenario_count
            for player_id, total in player_points.items()
        }
        for gameweek, player_points in totals.items()
    }


def plan_with_utility(
    current_state: PlanningState,
    scenarios: Sequence[Mapping[int, Mapping[str | int, float]]] | ScenarioResult,
    transition_fn: Callable[[PlanningState, GWPlan], PlanningState],
    *,
    candidate_pool: Sequence[Player] | None = None,
    player_registry: Mapping[str, Player] | None = None,
) -> PlanningResult:
    """
    High-level entry point for the Planning module.
    
    Args:
        current_state: The starting state of the FPL team.
        scenarios: ScenarioResult from ``uncertainty`` or a sequence of
            ``{gameweek: {player_id: sampled_points}}`` mappings.
        transition_fn: The FPL rule transition function (state, plan) -> next_state.
        candidate_pool: Eligible targets at the planning cutoff, with position,
            club, and price data.
        player_registry: Metadata for current squad players and transfer targets.
            It must include current squad metadata unless those players are also
            present in ``candidate_pool``. When using ``fpl.transfers.transition_fn``,
            bind the same registry to that callback so it updates the bank using
            the same player prices.
        
    Returns:
        Best plan sequence and its estimated expected utility.
    """
    # The objective is linear in player points, so the mean forecast gives the
    # same expected utility as evaluating every sampled outcome separately.
    sampled_forecasts = _scenario_forecasts(scenarios)
    expected_forecasts = _mean_forecasts(sampled_forecasts)

    objective = PlanningObjective(point_forecasts=expected_forecasts)
    search = PlanningSearch(
        objective,
        candidate_pool=candidate_pool,
        player_registry=player_registry,
    )

    plans = search.plan(current_state, sampled_forecasts, transition_fn)
    return PlanningResult(tuple(plans), search.best_utility)


def plan(
    current_state: PlanningState,
    scenarios: Sequence[Mapping[int, Mapping[str | int, float]]] | ScenarioResult,
    transition_fn: Callable[[PlanningState, GWPlan], PlanningState],
    *,
    candidate_pool: Sequence[Player] | None = None,
    player_registry: Mapping[str, Player] | None = None,
) -> list[GWPlan]:
    """Return the best Gameweek plan sequence using the established interface.

    The optional player metadata enables transfer search. Existing callers that
    omit it continue to receive legal no-transfer lineups.
    """
    return list(
        plan_with_utility(
            current_state,
            scenarios,
            transition_fn,
            candidate_pool=candidate_pool,
            player_registry=player_registry,
        ).plans
    )


__all__ = ["PlanningResult", "PlanningSearch", "plan", "plan_with_utility"]
