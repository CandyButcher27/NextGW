from typing import Dict, List
from .state import PlanningState
from .actions import GWPlan

class PlanningObjective:
    """
    Calculates the utility of a plan.
    Utility = (Expected Points from XI) - (Transfer Hit Costs).
    """
    def __init__(self, point_forecasts: Dict[int, Dict[str, float]], transfer_cost: float = 4.0):
        """
        Args:
            point_forecasts: Map of {gw: {player_id: expected_points}}
            transfer_cost: Points deducted for a transfer hit.
        """
        self.point_forecasts = point_forecasts
        self.transfer_cost = transfer_cost

    def calculate_gw_utility(self, state: PlanningState, plan: GWPlan) -> float:
        """
        Calculates the utility for a single Gameweek.
        """
        # 1. Calculate points from Starting XI
        gw = state.gameweek
        forecasts = self.point_forecasts.get(gw, {})
        
        # Expected points from the starting XI
        xi_points = sum(forecasts.get(pid, 0.0) for pid in plan.lineup.starting_xi)
        
        # Captaincy bonus (2x points)
        captain_id = plan.lineup.captain
        xi_points += forecasts.get(captain_id, 0.0)
        
        # 2. Calculate transfer costs
        # We assume state.free_transfers is updated by the transition function
        # If we use more transfers than available, we subtract the cost
        # This is a simplified version; the actual transition logic will handle the FT count
        num_transfers = len(plan.transfers)
        cost = 0.0
        if num_transfers > state.free_transfers:
            cost = (num_transfers - state.free_transfers) * self.transfer_cost
            
        return xi_points - cost

    def calculate_total_utility(self, state_sequence: List[PlanningState], plan_sequence: List[GWPlan]) -> float:
        """
        Calculates cumulative utility across the planning horizon.
        """
        total = 0.0
        for state, plan in zip(state_sequence, plan_sequence):
            total += self.calculate_gw_utility(state, plan)
        return total
