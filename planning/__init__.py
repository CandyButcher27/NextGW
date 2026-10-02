from typing import List, Dict
from .state import PlanningState
from .actions import GWPlan
from .objective import PlanningObjective
from .search import PlanningSearch

def plan(current_state: PlanningState, scenarios: List[Dict], transition_fn) -> List[GWPlan]:
    """
    High-level entry point for the Planning module.
    
    Args:
        current_state: The starting state of the FPL team.
        scenarios: A list of point forecast scenarios.
        transition_fn: The FPL rule transition function (state, plan) -> next_state.
        
    Returns:
        A sequence of GWPlans for the 4-GW horizon.
    """
    # Use the first scenario as the primary forecast for the objective
    # In a full uncertainty implementation, we would average utility across all scenarios
    primary_forecast = scenarios[0] if scenarios else {}
    
    objective = PlanningObjective(point_forecasts=primary_forecast)
    search = PlanningSearch(objective)
    
    return search.plan(current_state, scenarios, transition_fn)
