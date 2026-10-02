import pytest
from planning.state import PlanningState
from planning.actions import GWPlan, LineupAction
from planning.objective import PlanningObjective

def test_captain_doubling():
    # Forecasts: p1=10, p2=5
    point_forecasts = {0: {'p1': 10.0, 'p2': 5.0}}
    obj = PlanningObjective(point_forecasts)
    
    # State: GW 0, 1 FT
    state = PlanningState(0, (('p1', 'MID'), ('p2', 'MID')), 100.0, 1)
    
    # Plan: p1 is captain
    plan_p1_cap = GWPlan(transfers=[], lineup=LineupAction(['p1', 'p2'], 'p1', 'p2'))
    # Expected: p1(10) + p2(5) + captain_p1(10) = 25.0
    assert obj.calculate_gw_utility(state, plan_p1_cap) == 25.0

    # Plan: p2 is captain
    plan_p2_cap = GWPlan(transfers=[], lineup=LineupAction(['p1', 'p2'], 'p2', 'p1'))
    # Expected: p1(10) + p2(5) + captain_p2(5) = 20.0
    assert obj.calculate_gw_utility(state, plan_p2_cap) == 20.0

def test_transfer_hit_cost():
    # Forecasts: generic
    point_forecasts = {0: {'p1': 10.0}}
    obj = PlanningObjective(point_forecasts, transfer_cost=4.0)
    
    # State: GW 0, 0 Free Transfers (Must take hits)
    state = PlanningState(0, (('p1', 'MID'),), 100.0, 0)
    
    # Plan: 1 transfer (should cost 4.0)
    plan_1_transfer = GWPlan(transfers=['t1'], lineup=LineupAction(['p1'], 'p1', 'p1'))
    # Expected: p1(10) + cap_p1(10) - hit(4) = 16.0
    assert obj.calculate_gw_utility(state, plan_1_transfer) == 16.0

    # Plan: 2 transfers (should cost 8.0)
    plan_2_transfers = GWPlan(transfers=['t1', 't2'], lineup=LineupAction(['p1'], 'p1', 'p1'))
    # Expected: p1(10) + cap_p1(10) - hits(8) = 12.0
    assert obj.calculate_gw_utility(state, plan_2_transfers) == 12.0

def test_free_transfers_no_cost():
    point_forecasts = {0: {'p1': 10.0}}
    obj = PlanningObjective(point_forecasts, transfer_cost=4.0)
    
    # State: GW 0, 2 Free Transfers
    state = PlanningState(0, (('p1', 'MID'),), 100.0, 2)
    
    # Plan: 1 transfer (should be free)
    plan_1_transfer = GWPlan(transfers=['t1'], lineup=LineupAction(['p1'], 'p1', 'p1'))
    # Expected: p1(10) + cap_p1(10) - 0 = 20.0
    assert obj.calculate_gw_utility(state, plan_1_transfer) == 20.0
