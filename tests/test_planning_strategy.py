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


def test_planner_waits_for_better_triple_captain_week_but_greedy_does_not():
    from baselines.greedy import GreedyStrategy

    def forecaster(history, season, gameweek, horizon):
        base = {f"p{i}": 1.0 for i in range(15)}
        weeks = {5: base | {"p7": 5.0}, 6: base | {"p7": 15.0}}
        return {gw: weeks.get(gw, base) for gw in range(gameweek, gameweek + horizon)}

    history = make_history({})
    chips = ("TripleCaptain",)
    greedy = GreedyStrategy(forecaster=forecaster, chips=chips).decide(make_state(), history, SEASON, 5)
    planner = PlannerStrategy(horizon=2, forecaster=forecaster, chips=chips).decide(make_state(), history, SEASON, 5)
    assert greedy.chip is not None and greedy.chip.chip_name == "TripleCaptain"
    assert planner.chip is None


def test_used_chip_is_not_offered_again():
    from planning.state import PlanningState

    history = make_history({})
    state = make_state()
    used = PlanningState(state.gameweek, state.squad, state.budget, state.free_transfers, frozenset({"TripleCaptain"}))
    plan = PlannerStrategy(horizon=1, chips=("TripleCaptain",)).decide(used, history, SEASON, 5)
    assert plan.chip is None
