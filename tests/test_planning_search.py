import pytest
from planning.state import PlanningState
from planning.actions import GWPlan, LineupAction, TransferAction
from planning.objective import PlanningObjective
from planning.search import PlanningSearch

def mock_transition(state, plan):
    """Simple mock transition: increment GW and keep state same."""
    return PlanningState(
        gameweek=state.gameweek + 1,
        squad=state.squad,
        budget=state.budget,
        free_transfers=state.free_transfers,
        chips_used=state.chips_used
    )

def test_beam_search_optimal_path():
    # Setup: Forecasts where a specific sequence of actions is clearly better
    # GW 0: Player A (10 pts), Player B (2 pts)
    # GW 1: Player A (2 pts), Player B (10 pts)
    point_forecasts = {
        0: {"p1": 10.0, "p2": 2.0},
        1: {"p1": 2.0, "p2": 10.0},
        2: {"p1": 5.0, "p2": 5.0},
        3: {"p1": 5.0, "p2": 5.0},
    }
    
    obj = PlanningObjective(point_forecasts)
    search = PlanningSearch(obj, beam_width=2)
    
    # Mock candidate generation to provide two choices per GW
    def mock_candidates(state):
        # Plan 1: Pick p1
        p1_plan = GWPlan(transfers=[], lineup=LineupAction(["p1"], "p1", "p2"))
        # Plan 2: Pick p2
        p2_plan = GWPlan(transfers=[], lineup=LineupAction(["p2"], "p2", "p1"))
        return [p1_plan, p2_plan]
    
    search._get_candidate_plans = mock_candidates
    
    initial_state = PlanningState(0, {"p1": "MID", "p2": "MID"}, 100.0, 1)
    
    result = search.plan(initial_state, [], mock_transition)
    
    assert len(result) == 4
    # The search should have picked the highest points for each GW
    # GW 0: p1 (10+10=20), GW 1: p2 (10+10=20)
    assert result[0].lineup.captain == "p1"
    assert result[1].lineup.captain == "p2"

if __name__ == "__main__":
    pytest.main([__file__])
