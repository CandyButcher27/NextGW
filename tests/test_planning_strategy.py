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


def test_discount_applies_to_transfer_ranking():
    from baselines.common import active_pool, player_registry
    from planning.objective import PlanningObjective
    from planning.search import PlanningSearch

    now = {f"p{i}": 2.0 for i in range(15)} | {"p7": 0.0, "p8": 1.0, "star_mid": 3.0}
    forecasts = {5: now, 6: now | {"p7": 50.0}}
    history = make_history({})
    registry = player_registry(history, SEASON)

    def sold(discount):
        search = PlanningSearch(
            PlanningObjective(forecasts, discount=discount),
            horizon=2,
            candidate_pool=active_pool(history, SEASON, registry),
            player_registry=registry,
        )
        return {t.player_out for plan in search._get_candidate_plans(make_state()) for t in plan.transfers if t.player_in == "star_mid"}

    assert sold(1.0) == {"p8"}
    assert sold(0.01) == {"p7"}
