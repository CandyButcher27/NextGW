from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING

from uncertainty.scenarios import ScenarioResult

from .state import PlanningState
from .actions import GWPlan
from .objective import PlanningObjective

if TYPE_CHECKING:
    from fpl.squad import Player


class PlanningSearch:
    """
    Implements a bounded search (Beam Search) to find the best 4-GW plan.
    """
    def __init__(
        self,
        objective: PlanningObjective,
        beam_width: int = 10,
        horizon: int = 4,
        *,
        candidate_pool: Sequence[Player] | None = None,
        player_registry: Mapping[str, Player] | None = None,
    ) -> None:
        self.objective = objective
        self.beam_width = beam_width
        self.horizon = horizon
        self.best_utility: float | None = None
        self.candidate_pool = tuple(candidate_pool) if candidate_pool is not None else None
        self.player_registry = {
            str(player_id): player
            for player_id, player in (player_registry or {}).items()
        }

    def plan(
        self,
        initial_state: PlanningState,
        scenarios: Sequence[Mapping[int, Mapping[str | int, float]]] | ScenarioResult,
        transition_fn: Callable[[PlanningState, GWPlan], PlanningState],
    ) -> list[GWPlan]:
        """
        Search for the optimal sequence of GWPlans.
        
        Args:
            initial_state: Starting state of the team.
            scenarios: Sampled points, normalized by :func:`planning.plan`.
            transition_fn: Function (state, plan) -> next_state.
        """
        # Beam: List of tuples (cumulative_utility, current_state, plan_history)
        self.best_utility = None
        beam = [(0.0, initial_state, [])]
        
        horizon = self.horizon
        for _ in range(horizon):
            new_beam = []
            
            for utility, state, history in beam:
                # 1. Generate legal candidate plans for this Gameweek.
                candidates = self._get_candidate_plans(state)
                
                for plan in candidates:
                    # 2. Transition to next state
                    next_state = transition_fn(state, plan)
                    
                    # 3. Calculate utility for this step
                    step_utility = self.objective.calculate_gw_utility(state, plan)
                    total_utility = utility + step_utility
                    
                    new_beam.append((total_utility, next_state, history + [plan]))
            
            # Keep only the top N (beam width) candidates
            new_beam.sort(key=lambda x: x[0], reverse=True)
            beam = new_beam[:self.beam_width]
            
        # Return the plan history and retain its score for the result wrapper.
        self.best_utility = beam[0][0] if beam else None
        return beam[0][2] if beam else []

    def _get_candidate_plans(self, state: PlanningState) -> list[GWPlan]:
        """Generate legal lineups and transfer candidates for the current Gameweek."""
        from fpl.transfers import generate_candidate_plans

        if self.candidate_pool:
            if isinstance(state.squad, Mapping):
                current_player_ids = {str(player_id) for player_id in state.squad}
            else:
                current_player_ids = {
                    str(item[0]) if isinstance(item, (tuple, list)) else str(item)
                    for item in state.squad
                }
            known_player_ids = set(self.player_registry)
            known_player_ids.update(player.player_id for player in self.candidate_pool)
            missing_player_ids = sorted(current_player_ids - known_player_ids)
            if missing_player_ids:
                raise ValueError(
                    "Player metadata is required for current squad members when "
                    f"generating transfers; missing: {missing_player_ids}"
                )

        remaining: dict[str, float] = {}
        for gameweek, points in self.objective.point_forecasts.items():
            if gameweek >= state.gameweek:
                for player_id, value in points.items():
                    remaining[player_id] = remaining.get(player_id, 0.0) + value
        return generate_candidate_plans(
            state,
            candidate_pool=self.candidate_pool,
            expected_points=self.objective.point_forecasts.get(state.gameweek, {}),
            player_registry=self.player_registry,
            ranking_points=remaining,
        )
