from planning.strategy import PlannerStrategy
from tests.test_baselines_strategies import SEASON, make_history, make_state, squad_after


def test_planner_strategy_returns_legal_plan_for_decision_gameweek():
    history = make_history({"star_mid": [12, 12, 12, 12], "p7": [0, 0, 0, 0]})
    state = make_state()
    plan = PlannerStrategy(horizon=2).decide(state, history, SEASON, 5)
    assert [(t.player_out, t.player_in) for t in plan.transfers] == [("p7", "star_mid")]
    assert set(plan.lineup.starting_xi) <= squad_after(state, plan)


def test_planner_strategy_uses_injected_forecaster():
    calls = []

    def forecaster(history, season, gameweek, horizon):
        calls.append((season, gameweek, horizon))
        return {gw: {"p0": 1.0} for gw in range(gameweek, gameweek + horizon)}

    PlannerStrategy(horizon=3, forecaster=forecaster).decide(make_state(), make_history({}), SEASON, 5)
    assert calls == [(SEASON, 5, 3)]
